# goals/notifications.py
import random
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# English tips for when goals are NOT met
ENGLISH_TIPS_NOT_MET = [
    "Meeting your physical activity goals takes a lot of determination but the results are worth it. This is exactly what Linda learned during her GDM experience. Linda challenged herself to walk every evening - rain or shine or snow - and saw great changes in her blood sugar levels and her overall wellbeing. Learn more about Linda's story here: https://www.activepatient.ca/perspectives-en/",
    "For some women the hardest part about increasing their physical activity is just getting started. But for most it gets easier once they start seeing the results: more energy, better sleep, less anxiety. Sound good? Learn more about the benefits and how to get started https://www.activepatient.ca/activity-2/",
    "The opposite of stepping is sitting. Break up the sitting! After 30 minutes of sitting, get up, stand, stretch, and- when possible- step!",
    "Adding a walk into your day will take you 'steps' towards your daily goal, but 'leaps' towards your overall health during pregnancy!",
    "Taking public transport- bus, subway, metro, train- will usually mean more steps than if you drive door to door. Do it if you can!",
    "Partners who walk together are bringing their family closer to better health.",
    "Do you already have kids at home? How about going to the park? Try to get up from that park bench and put away your phone.",
    "How about putting some music on and dancing? Let's see those dance steps!",
    "Feeling tired? A little walk or a few steps may be what you need to perk up.",
    "Know that even if your total steps today is not as high as you planned, there is always tomorrow to try again.",
    "Higher steps mean better blood sugar control.",
    "More steps can mean a healthier pregnancy.",
    "If you step more, you may sleep better.",
    "You may have not met the step goal today but be proud of every step you did take because every step counts. Keep stepping!",
    "One step taken is one step closer to your goal! Think about ways that you can perhaps add steps to your day when you normally would be sitting.",
    "Could you walk instead of drive? Think about it.",
    "When you drive somewhere, park the car a bit further from where you are going- you will have to step more."
]

# English tips for when goals ARE met
ENGLISH_TIPS_MET = [
    "You are on track! Keep up the great work.",
    "Well done. Every step counts towards better health.",
    "You are doing well! Maybe you can inspire others to join your march to good health.",
    "Good work! If you walk outside in winter, remember to dress in layers and wear warm boots with good treads. Walk carefully and don't fall. However in summer, if it's hot outside, make sure to take some water with you to stay hydrated!",
    "Congratulations on meeting your target!",
    "Hard work can pay off. Good job.",
    "High five. You met last week's goals.",
    "Bravo! You are doing well.",
    "Excellent. Persistence can pay off.",
    "Good job! Your commitment to health is showing.",
    "Two thumbs up! Keep it up- one step forward at a time.",
    "Pat yourself on the back. You are on track.",
    "Give yourself a hug. You are getting there, one step and a time.",
    "Yay! You are working hard.",
    "Hooray! Celebrate your efforts and achievements.",
    "Cheers to you! You are reaching your targets.",
    "Hang in there- you are doing great.",
    "Wow! Each step is an investment in health.",
    "Yahoo! You are doing really well."
]

# French tips for when goals are NOT met
FRENCH_TIPS_NOT_MET = [
    "À vos marques: Pour certaines femmes, la partie la plus difficile quant à augmenter leur activité physique est de commencer. Mais pour la plupart, cela devient plus facile une fois qu'elles voient les résultats: plus d'énergie, meilleur sommeil, moins d'anxiété. Ça sonne bien? En savoir plus sur les avantages et comment commencer. Cliquez ici pour en savoir plus: https://www.activepatient.ca/fr/activity-2",
    "Atteindre vos objectifs d'activité physique demande beaucoup de détermination, mais les résultats en valent la peine. C'est exactement ce que Katherine a appris au cours de son expérience de grossesse avec diabète gestationnel. Katherine s'est mise au défi de marcher tous les soirs, qu'il pleuve ou qu'il neige, et a constaté de grands changements dans son taux de glycémie et son bien-être général. En savoir plus sur l'histoire de Katherine ici: https://www.activepatient.ca/fr/perspectives-en/",
    "Le contraire de marcher est de s'asseoir. Arrêtez de vous asseoir! Après 30 minutes assise, levez-vous, restez debout, étirez-vous et - quand possible - marchez!",
    "Ajouter une promenade à votre journée vous amènera à «des pas» vers votre objectif quotidien, mais des «sauts» vers votre santé globale pendant la grossesse!",
    "Utiliser le transport en commun - bus, métro, train - signifiera généralement plus de marches que si vous conduisiez de porte à porte. Faites-le si vous le pouvez!",
    "Les partenaires qui marchent ensemble rapprochent leur famille d'une meilleure santé.",
    "Avez-vous déjà des enfants à la maison? Que diriez-vous d'aller au parc? Essayez de vous lever de ce banc et de ranger votre téléphone.",
    "Pourquoi ne pas mettre de la musique et danser? Laissez-nous voir ces pas de danse!",
    "Vous vous sentez fatiguée? Une petite promenade ou faire quelques pas peut être ce dont vous avez besoin pour vous revigorer.",
    "Sachez que même si le nombre total de vos pas aujourd'hui n'est pas aussi élevé que prévu, il y a toujours le lendemain pour réessayer.",
    "Un nombre plus élevé de pas signifie un meilleur contrôle de la glycémie.",
    "Marcher davantage peut signifier une grossesse plus saine.",
    "Si vous marchez davantage, vous dormirez peut-être mieux.",
    "Vous n'avez peut-être pas atteint l'objectif de marche aujourd'hui, mais soyez fière de chaque pas que vous avez faits, car chaque pas compte. Continuez à marcher!",
    "Un pas marché est un pas plus proche de votre objectif! Pensez à des moyens d'ajouter la marche à votre journée lorsque vous êtes normalement assise.",
    "Lorsque vous conduisez quelque part, garez la voiture un peu plus loin de l'endroit où vous vous dirigez - vous devrez ainsi marcher davantage.",
    "Pour augmenter vos pas - garez la voiture un peu plus loin de votre destination et si vous utiliser le transport en commun débarquez un arrêt avant le votre."
]

# French tips for when goals ARE met
FRENCH_TIPS_MET = [
    "Vous êtes sur la bonne voie! Continuez le bon travail.",
    "Bravo! Chaque pas compte pour une meilleure santé.",
    "Vous vous débrouillez bien! Peut-être vous pouvez inspirer les autres à se joindre à votre marche vers une bonne santé.",
    "En été, s'il fait chaud dehors, assurez-vous de prendre de l'eau avec vous pour rester hydratée.",
    "Félicitations pour avoir atteint votre objectif!",
    "Le travail acharné peut porter fruit. Bon travail.",
    "Tape m'en cinq. Vous avez atteint les objectifs de la semaine dernière.",
    "Bravo! Vous vous débrouillez bien.",
    "Excellent. La persistance peut porter fruit.",
    "Bon travail! Votre engagement pour la santé est visible.",
    "Deux pouces vers le haut! Continuez- un pas en avant à la fois.",
    "Donnez-vous une bonne tape dans le dos. Vous êtes sur la bonne voie.",
    "Faites-vous un câlin. Vous y arrivez, un pas à la fois.",
    "Yay! Vous travaillez fort.",
    "Hourra! Célébrez vos efforts et vos réalisations.",
    "Bravo à vous! Vous atteignez vos objectifs.",
    "Tenez bien- vous vous débrouillez bien.",
    "Wow! Chaque pas est un investissement dans la santé.",
    "Yahoo! Vous vous débrouillez vraiment bien."
]

def get_random_tip(language, goal_met):
    """
    Get a random motivational tip based on language and whether goal was met.
    
    Args:
        language: 'en' or 'fr'
        goal_met: True if previous goal was met, False if not, None for first week
    
    Returns:
        str: Random tip message
    """
    if language == 'fr':
        if goal_met:
            return random.choice(FRENCH_TIPS_MET)
        else:
            return random.choice(FRENCH_TIPS_NOT_MET)
    else:  # Default to English
        if goal_met:
            return random.choice(ENGLISH_TIPS_MET)
        else:
            return random.choice(ENGLISH_TIPS_NOT_MET)

def create_email_content(participant, goal_data):
    """
    Create bilingual email content based on participant's language preference.
    """
    language = participant.language
    average_steps = goal_data.get('average_steps')
    new_target = goal_data.get('new_target')
    target_was_met = goal_data.get('target_was_met')
    previous_target = goal_data.get('previous_target')
    
    # Handle insufficient data case
    if average_steps == "insufficient data":
        if language == 'fr':
            subject = "Objectif de pas maintenu"
            message_lines = [
                "Nous n'avons pas suffisamment de données de pas cette semaine.",
                f"Votre objectif reste {new_target} pas par jour."
            ]
            tip = get_random_tip('fr', None)
            message_lines.append(f"\n{tip}")
        else:
            subject = "Step Target Maintained"
            message_lines = [
                "We don't have enough step data from this week.",
                f"Your target remains {new_target} steps per day."
            ]
            tip = get_random_tip('en', None)
            message_lines.append(f"\n{tip}")
        
        return subject, "\n".join(message_lines)
    
    # Normal case with valid step data
    if language == 'fr':
        subject = "Résumé du nombre de pas et nouvel objectif"
        message_lines = [
            f"La semaine dernière vous avez fait un moyen de {average_steps} pas par jour."
        ]
        
        if target_was_met is not None and previous_target:
            if target_was_met:
                message_lines.append(f"Vous avez fait plus que le but de la semaine dernière qui était {previous_target} pas par jours.")
            else:
                message_lines.append(f"Vous avez fait moins que le but de la semaine dernière qui était {previous_target} pas par jours.")
        
        message_lines.append(f"Cela signifie que votre objectif pour la semaine prochaine est {new_target} pas par jour.")
        tip = get_random_tip('fr', target_was_met)
        message_lines.append(f"\n{tip}")
        
    else:
        subject = "Step Count Summary and New Target"
        message_lines = [
            f"Last week you did an average of {average_steps} steps per day."
        ]
        
        if target_was_met is not None and previous_target:
            comparison = "more" if target_was_met else "less"
            message_lines.append(f"This was {comparison} than last week's target of {previous_target} steps per day.")
        
        message_lines.append(f"Your target for next week is {new_target} steps per day.")
        tip = get_random_tip('en', target_was_met)
        message_lines.append(f"\n{tip}")
    
    return subject, "\n".join(message_lines)
    
    
def send_goal_notification(participant, goal_data):
    """
    Send email notification to participant with their new weekly goal.
    
    Args:
        participant: Participant instance
        goal_data: Dictionary containing goal information from run_weekly_algorithm
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    from django.utils import timezone
    
    try:
        subject, message_body = create_email_content(participant, goal_data)
        
        # Get email settings
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'john.dowling@rimuhc.ca')
        recipient_email = participant.user.email
        
        # Send email
        email_sent = False
        try:
            send_mail(
                subject=subject,
                message=message_body,
                from_email=from_email,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            email_sent = True
            logger.info(f"Goal notification sent to {recipient_email} in {participant.language}")
            
            # SUCCESS - Clear any previous notification errors
            participant.status_flags["send_notification_fail"] = False
            participant.status_flags.pop("send_notification_last_error", None)
            participant.status_flags.pop("send_notification_last_error_time", None)
            
        except Exception as email_error:
            error_msg = f"Email sending failed: {str(email_error)}"
            logger.warning(error_msg)
            
            # LOG ERROR to status_flags
            participant.status_flags["send_notification_fail"] = True
            participant.status_flags["send_notification_last_error"] = error_msg
            participant.status_flags["send_notification_last_error_time"] = timezone.now().isoformat()
        
        # Log message to participant's history (even if email failed)
        message_entry = {
            "date": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            "subject": subject,
            "content": message_body,
            "language": participant.language,
            "goal_data": {
                "average_steps": goal_data.get('average_steps'),
                "new_target": goal_data.get('new_target'),
                "target_was_met": goal_data.get('target_was_met')
            },
            "email_sent": email_sent
        }
        
        # Add to message history
        message_history = participant.message_history or []
        message_history.append(message_entry)
        participant.message_history = message_history
        participant.save(update_fields=['message_history', 'status_flags'])
        
        logger.info(f"Message logged for participant {participant.id}")
        return email_sent
        
    except Exception as e:
        error_msg = f"Failed to send/log goal notification: {str(e)}"
        logger.error(error_msg)
        
        # LOG ERROR to status_flags
        participant.status_flags["send_notification_fail"] = True
        participant.status_flags["send_notification_last_error"] = error_msg
        participant.status_flags["send_notification_last_error_time"] = timezone.now().isoformat()
        participant.save(update_fields=['status_flags'])
        
        return False