# core/management/commands/backup_database.py
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
import subprocess
import os
import logging
from datetime import datetime, timedelta
import dropbox
from dropbox.exceptions import ApiError, AuthError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create PostgreSQL backup and upload to Dropbox with automatic rotation'
    
    # Configuration
    RETENTION_WEEKS = 52
    BACKUP_FOLDER = '/PartnerStepsT2D/backups'  # Folder in Dropbox
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test Dropbox connection and exit',
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(f"Starting backup at {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No actual backup or upload\n"))
        
        # Test connection mode
        if options['test_connection']:
            return self.test_dropbox_connection()
        
        backup_file = None  # Track the file for cleanup
        try:
            # Step 1: Create database dump
            self.stdout.write("Step 1: Creating database dump...")
            backup_file = self.create_database_dump()
            
            if not backup_file:
                raise Exception("Failed to create database dump")
            
            self.stdout.write(self.style.SUCCESS(f"✓ Created dump: {backup_file}"))
            
            # Step 2: Upload to Dropbox
            self.stdout.write("\nStep 2: Uploading to Dropbox...")
            dropbox_path = self.upload_to_dropbox(backup_file)
            
            if not dropbox_path:
                raise Exception("Failed to upload to Dropbox")
            
            self.stdout.write(self.style.SUCCESS(f"✓ Uploaded to: {dropbox_path}"))
            
            # Step 3: Clean up old backups
            self.stdout.write("\nStep 3: Cleaning up old backups...")
            deleted_count = self.cleanup_old_backups()
            self.stdout.write(self.style.SUCCESS(f"✓ Deleted {deleted_count} old backup(s)"))
            
            # Success!
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            success_message = f"""
Backup completed successfully in {duration:.1f} seconds

Database: {self.get_database_name()}
Backup file: {dropbox_path}
Size: {self.get_file_size_mb(backup_file):.2f} MB
Retention: {self.RETENTION_WEEKS} weeks
"""
            
            self.stdout.write(self.style.SUCCESS("\n" + "="*70))
            self.stdout.write(self.style.SUCCESS(success_message))
            self.stdout.write(self.style.SUCCESS("="*70))
            
            # Send success email
            self.send_notification_email(
                success=True,
                message=success_message,
                backup_path=dropbox_path
            )
            
        except Exception as e:
            error_message = f"Backup failed: {str(e)}"
            logger.error(error_message)
            self.stderr.write(self.style.ERROR(f"\n✗ {error_message}"))
            
            # Send failure email
            self.send_notification_email(
                success=False,
                message=error_message,
                error=str(e)
            )
            
            raise
        finally:
            # Always clean up local file, even on failure
            if backup_file and not self.dry_run and os.path.exists(backup_file):
                try:
                    os.remove(backup_file)
                    self.stdout.write(self.style.SUCCESS(f"✓ Cleaned up local file"))
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup {backup_file}: {cleanup_error}")
    
    def get_database_config(self):
        """Extract database configuration from Django settings."""
        db_config = settings.DATABASES['default']
        
        # Handle dj-database-url format
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            # Parse DATABASE_URL: postgres://user:pass@host:port/dbname
            from urllib.parse import urlparse, unquote
            parsed = urlparse(db_url)
            
            # Handle both postgres:// and postgresql:// schemes
            if parsed.scheme not in ('postgres', 'postgresql'):
                logger.warning(f"Unexpected database scheme: {parsed.scheme}")
            
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'user': unquote(parsed.username) if parsed.username else None,
                'password': unquote(parsed.password) if parsed.password else None,
                'name': parsed.path[1:],  # Remove leading slash
            }
        
        return {
            'host': db_config.get('HOST', 'localhost'),
            'port': db_config.get('PORT', 5432),
            'user': db_config.get('USER'),
            'password': db_config.get('PASSWORD'),
            'name': db_config.get('NAME'),
        }
    
    def get_database_name(self):
        """Get the database name for logging."""
        config = self.get_database_config()
        return config['name']
    
    def create_database_dump(self):
        """Create a compressed PostgreSQL dump using pg_dump."""
        if self.dry_run:
            return "/tmp/gdm-backup-dry-run.dump"
        
        config = self.get_database_config()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"gdm-backup-{timestamp}.dump"
        backup_path = os.path.join('/tmp', backup_filename)
        
        # Build pg_dump command
        # Using custom format (-Fc) which is compressed and optimal for pg_restore
        cmd = [
            'pg_dump',
            '-Fc',  # Custom format (compressed)
            '-h', config['host'],
            '-p', str(config['port']),
            '-U', config['user'],
            '-d', config['name'],
            '-f', backup_path,
        ]
        
        # Set password via environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = config['password']
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Verify file was created and has content
            if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                return backup_path
            else:
                logger.error("Backup file not created or is empty")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"pg_dump failed: {e.stderr}")
            return None
    
    def upload_to_dropbox(self, local_file):
        """Upload backup file to Dropbox."""
        if self.dry_run:
            return f"{self.BACKUP_FOLDER}/{os.path.basename(local_file)}"
        
        # Get Dropbox token from settings
        dropbox_token = getattr(settings, 'DROPBOX_ACCESS_TOKEN', None)
        if not dropbox_token:
            raise Exception("DROPBOX_ACCESS_TOKEN not configured in settings")
        
        try:
            dbx = dropbox.Dropbox(dropbox_token)
            
            # Verify connection
            dbx.users_get_current_account()
            
            # Ensure backup folder exists
            try:
                dbx.files_get_metadata(self.BACKUP_FOLDER)
            except ApiError as e:
                if e.error.is_path() and e.error.get_path().is_not_found():
                    # Folder doesn't exist, create it
                    dbx.files_create_folder_v2(self.BACKUP_FOLDER)
                    logger.info(f"Created Dropbox folder: {self.BACKUP_FOLDER}")
                else:
                    raise
            
            # Prepare Dropbox path
            filename = os.path.basename(local_file)
            dropbox_path = f"{self.BACKUP_FOLDER}/{filename}"
            
            # Upload file
            with open(local_file, 'rb') as f:
                dbx.files_upload(
                    f.read(),
                    dropbox_path,
                    mode=dropbox.files.WriteMode.overwrite
                )
            
            return dropbox_path
            
        except AuthError as e:
            logger.error(f"Dropbox authentication failed: {e}")
            raise Exception("Dropbox authentication failed. Check DROPBOX_ACCESS_TOKEN.")
        except ApiError as e:
            logger.error(f"Dropbox API error: {e}")
            raise
    
    def cleanup_old_backups(self):
        """Delete backups older than RETENTION_WEEKS."""
        if self.dry_run:
            return 0
        
        dropbox_token = getattr(settings, 'DROPBOX_ACCESS_TOKEN', None)
        if not dropbox_token:
            return 0
        
        try:
            dbx = dropbox.Dropbox(dropbox_token)
            
            # List all files in backup folder
            result = dbx.files_list_folder(self.BACKUP_FOLDER)
            files = result.entries
            
            # Calculate cutoff date - timezone.now() returns UTC-aware datetime
            cutoff_date = timezone.now() - timedelta(weeks=self.RETENTION_WEEKS)
            
            deleted_count = 0
            for entry in files:
                if isinstance(entry, dropbox.files.FileMetadata):
                    # Both entry.server_modified (from Dropbox) and cutoff_date are UTC-aware
                    # so we can compare them directly
                    if entry.server_modified < cutoff_date:
                        dbx.files_delete_v2(entry.path_display)
                        deleted_count += 1
                        self.stdout.write(f"  Deleted: {entry.name}")
            
            return deleted_count
            
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                # Folder doesn't exist yet, that's okay
                return 0
            logger.error(f"Dropbox cleanup error: {e}")
            return 0
    
    def get_file_size_mb(self, filepath):
        """Get file size in MB."""
        if self.dry_run or not os.path.exists(filepath):
            return 0.0
        return os.path.getsize(filepath) / (1024 * 1024)
    
    def send_notification_email(self, success, message, backup_path=None, error=None):
        """Send email notification about backup status."""
        if self.dry_run:
            self.stdout.write("Would send email notification")
            return
        
        # Get email settings
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'john.dowling@rimuhc.ca')
        admin_emails = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', [from_email])
        
        # Handle both single email (string) and multiple emails (list)
        recipient_list = admin_emails if isinstance(admin_emails, list) else [admin_emails]
        
        if success:
            subject = "✓ Database Backup Successful"
            body = f"""Database Backup Completed Successfully

{message}

Dropbox Path: {backup_path}

This is an automated notification from the backup system.
"""
        else:
            subject = "✗ Database Backup FAILED"
            body = f"""Database Backup Failed

Error: {error}

Details:
{message}

Action Required: Please investigate the backup system immediately.

This is an automated notification from the backup system.
"""
        
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            logger.info(f"Sent backup notification email to {recipient_list}")
        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")
            # Don't raise - backup succeeded even if email failed
    
    def test_dropbox_connection(self):
        """Test Dropbox connection and display account info."""
        self.stdout.write("Testing Dropbox connection...\n")
        
        dropbox_token = getattr(settings, 'DROPBOX_ACCESS_TOKEN', None)
        
        if not dropbox_token:
            self.stderr.write(self.style.ERROR(
                "✗ DROPBOX_ACCESS_TOKEN not configured in settings"
            ))
            return
        
        try:
            dbx = dropbox.Dropbox(dropbox_token)
            account = dbx.users_get_current_account()
            
            self.stdout.write(self.style.SUCCESS("✓ Connection successful!"))
            self.stdout.write(f"\nAccount: {account.name.display_name}")
            self.stdout.write(f"Email: {account.email}")
            
            # Try to access backup folder
            try:
                result = dbx.files_list_folder(self.BACKUP_FOLDER)
                self.stdout.write(f"\n✓ Backup folder exists: {self.BACKUP_FOLDER}")
                self.stdout.write(f"  Contains {len(result.entries)} file(s)")
            except ApiError as e:
                if e.error.is_path() and e.error.get_path().is_not_found():
                    self.stdout.write(f"\n⚠ Backup folder does not exist yet: {self.BACKUP_FOLDER}")
                    self.stdout.write("  (Folder will be created automatically on first backup)")
                else:
                    raise
            
        except AuthError:
            self.stderr.write(self.style.ERROR(
                "✗ Authentication failed. Check your DROPBOX_ACCESS_TOKEN."
            ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"✗ Connection failed: {e}"))
