# core/management/commands/backup_database.py
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
import subprocess
import os
import logging
from datetime import datetime, timedelta
from google.cloud import storage
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create PostgreSQL backup and upload to Google Cloud Storage with automatic rotation'
    
    # Configuration
    RETENTION_WEEKS = 52
    BUCKET_NAME = 'partner-steps-backups'  # Your GCS bucket name
    BACKUP_FOLDER = 'backups'  # Folder within bucket
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test Google Cloud Storage connection and exit',
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(f"Starting backup at {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No actual backup or upload\n"))
        
        # Test connection mode
        if options['test_connection']:
            return self.test_gcs_connection()
        
        backup_file = None  # Track the file for cleanup
        try:
            # Step 1: Create database dump
            self.stdout.write("Step 1: Creating database dump...")
            backup_file = self.create_database_dump()
            
            if not backup_file:
                raise Exception("Failed to create database dump")
            
            self.stdout.write(self.style.SUCCESS(f"✓ Created dump: {backup_file}"))
            
            # Step 2: Upload to Google Cloud Storage
            self.stdout.write("\nStep 2: Uploading to Google Cloud Storage...")
            gcs_path = self.upload_to_gcs(backup_file)
            
            if not gcs_path:
                raise Exception("Failed to upload to Google Cloud Storage")
            
            self.stdout.write(self.style.SUCCESS(f"✓ Uploaded to: gs://{self.BUCKET_NAME}/{gcs_path}"))
            
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
Backup file: gs://{self.BUCKET_NAME}/{gcs_path}
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
                backup_path=f"gs://{self.BUCKET_NAME}/{gcs_path}"
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
    
    def get_gcs_client(self):
        """Get authenticated Google Cloud Storage client."""
        credentials_path = getattr(settings, 'GCS_CREDENTIALS_PATH', None)
        
        if not credentials_path:
            raise Exception("GCS_CREDENTIALS_PATH not configured in settings")
        
        if not os.path.exists(credentials_path):
            raise Exception(f"GCS credentials file not found: {credentials_path}")
        
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        return storage.Client(credentials=credentials, project=credentials.project_id)
    
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
    
    def upload_to_gcs(self, local_file):
        """Upload backup file to Google Cloud Storage."""
        if self.dry_run:
            return f"{self.BACKUP_FOLDER}/{os.path.basename(local_file)}"
        
        try:
            client = self.get_gcs_client()
            bucket = client.bucket(self.BUCKET_NAME)
            
            # Prepare GCS path
            filename = os.path.basename(local_file)
            blob_name = f"{self.BACKUP_FOLDER}/{filename}"
            blob = bucket.blob(blob_name)
            
            # Upload file
            blob.upload_from_filename(local_file)
            
            return blob_name
            
        except Exception as e:
            logger.error(f"Google Cloud Storage upload failed: {e}")
            raise Exception(f"Failed to upload to Google Cloud Storage: {str(e)}")
    
    def cleanup_old_backups(self):
        """Delete backups older than RETENTION_WEEKS."""
        if self.dry_run:
            return 0
        
        try:
            client = self.get_gcs_client()
            bucket = client.bucket(self.BUCKET_NAME)
            
            # List all blobs in backup folder
            blobs = bucket.list_blobs(prefix=f"{self.BACKUP_FOLDER}/")
            
            # Calculate cutoff date - timezone.now() returns UTC-aware datetime
            cutoff_date = timezone.now() - timedelta(weeks=self.RETENTION_WEEKS)
            
            deleted_count = 0
            for blob in blobs:
                # blob.time_created is timezone-aware UTC from Google Cloud
                if blob.time_created < cutoff_date:
                    blob.delete()
                    deleted_count += 1
                    self.stdout.write(f"  Deleted: {blob.name}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Google Cloud Storage cleanup error: {e}")
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

Google Cloud Storage Path: {backup_path}

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
    
    def test_gcs_connection(self):
        """Test Google Cloud Storage connection and display bucket info."""
        self.stdout.write("Testing Google Cloud Storage connection...\n")
        
        try:
            client = self.get_gcs_client()
            bucket = client.bucket(self.BUCKET_NAME)
            
            # Check if bucket exists and we have access
            if not bucket.exists():
                self.stderr.write(self.style.ERROR(
                    f"✗ Bucket does not exist: {self.BUCKET_NAME}"
                ))
                return
            
            self.stdout.write(self.style.SUCCESS("✓ Connection successful!"))
            self.stdout.write(f"\nBucket: {self.BUCKET_NAME}")
            self.stdout.write(f"Location: {bucket.location}")
            self.stdout.write(f"Storage class: {bucket.storage_class}")
            
            # List existing backups
            blobs = list(bucket.list_blobs(prefix=f"{self.BACKUP_FOLDER}/"))
            self.stdout.write(f"\n✓ Backup folder: {self.BACKUP_FOLDER}/")
            self.stdout.write(f"  Contains {len(blobs)} file(s)")
            
            if blobs:
                self.stdout.write("\n  Recent backups:")
                for blob in sorted(blobs, key=lambda b: b.time_created, reverse=True)[:5]:
                    size_mb = blob.size / (1024 * 1024)
                    self.stdout.write(f"    - {blob.name} ({size_mb:.2f} MB, {blob.time_created.strftime('%Y-%m-%d %H:%M')})")
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"✗ Connection failed: {e}"))
