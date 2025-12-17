# goals/notifications.py
import random
from django.core.mail import send_mail
from django.conf import settings
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

# English tips for when goals are NOT met
ENGLISH_TIPS_NOT_MET = [
  "Some people prefer walking first thing in the morning, others do it during lunchtime, and for some it is easier to walk during the evening. What time of the day works best for you?",
  "Many people find it easier to go walk with someone. Who would you like to invite to join you on a walk?",
  "Try analyzing what got in the way of your reaching your walking goals. What could you do differently this week to deal with these obstacles?",
  "New week, new opportunity to do things differently and to reach your goal!",
  "When in your day could you take 10 minutes to go on a short walk?",
  "For many people, a good way to increase their walking is by integrating it with other daily or weekly task. For example, try walking to your local grocery store at least once a week. It could be a great opportunity to buy some fresh foods!",
  "Add some steps while you are having fun! Bowling, dancing, or even going to the museum will help you naturally increase your step count. What’s a fun activity that you could plan to make you move more?",
  "Listening to music, listening to a podcast, talking with someone, or taking time for yourself while you walk. What would make your walk more enjoyable?",
  "Taking just a 10-minute walk after a meal is associated with several health benefits. After which meal could you try that?",
  "Where do you like to walk? In a park, in your favorite neighborhood, in the forest?",
  "Are there times in your week when you could you walk instead of drive? When would that be?",
  "Small changes add up: When you drive somewhere, you could park the car a bit further from where you are going- you will have to step more.",
  "Small changes add up: If you work outside the home, try to go see a colleague instead of emailing and move your phone away so you will need to stand to answer.",
  "Small changes add up: try taking the stairs instead of taking the elevator.",
  "Have you spent a lot of times in front of tv or watching at your phone? After 30 minutes of sitting, get up, stand, stretch, and walk for a few minutes. See how it makes you feel.",
  "Family who walk together are all becoming healthier. Who would you like to bring with you? Your partner, your kids, your parents, siblings?",
  "Do you have some friends or family members who are active people? Try planning an active social gathering with them.",
  "Remember that taking a few steps is always better than none.",
  "We all have days when it is harder to be active. Don’t worry it is normal. Tomorrow will be a new day",
  "Feeling low in energy? Our first response is often to sit and do less. However, for many people, just taking a 10-minute walk will make them feel better. Try it and see how it makes you feel"
]

# English tips for when goals ARE met
ENGLISH_TIPS_MET = [
	"You are on track! Keep up the great work.",
	"Well done. 😊",
	"You are doing well! ",
	"Keep going. You are creating new walking habits.",
	"Congratulations on meeting your target!",
	"Bravo! You are doing well.",
	"Excellent. Persistence can pay off.",
	"Good job! Your commitment to health is showing.",
	"Yay! You are working hard.",
	"Cheers to you! You are reaching your targets.",
]

# French tips for when goals are NOT met
FRENCH_TIPS_NOT_MET = [
  "Certaines personnes préfèrent marcher tôt le matin, d'autres le font pendant leur pause du midi, et pour d'autres encore, il est plus facile de marcher le soir. Quel moment de la journée vous convient le mieux ?",
  "Beaucoup de gens trouvent ça plus facile de marcher en compagnie de quelqu’un d’autre. Qui aimeriez-vous inviter à vous accompagner ?",
  "Essayez d'analyser ce qui vous a empêché d'atteindre vos objectifs de marche. Que pourriez-vous faire différemment cette semaine pour surmonter ces obstacles ?",
  "Une nouvelle semaine, une nouvelle occasion de faire les choses différemment et d'atteindre vos buts !",
  "À quel moment de la journée pourriez-vous prendre 10 minutes pour faire une petite marche ?",
  "Pour beaucoup de gens, un bon moyen d'augmenter leur temps de marche est de l'intégrer à d'autres tâches quotidiennes ou hebdomadaires. Par exemple, essayez de vous rendre à pied à votre épicerie locale au moins une fois par semaine. Cela pourrait aussi être une excellente occasion d'acheter des produits frais !",
  "Ajoutez quelques pas tout en vous amusant ! Les quilles, la danse ou même une visite au musée vous aideront à augmenter naturellement votre nombre de pas. Quelle activité amusante pourriez-vous prévoir pour bouger davantage ?",
  "Écouter de la musique, écouter un podcast, discuter avec quelqu'un ou prendre du temps pour vous pendant que vous marchez. Qu'est-ce qui rendrait votre promenade plus agréable ?",
  "Une promenade de seulement 10 minutes après un repas présente plusieurs avantages pour la santé. Après quel repas pourriez-vous essayer cela ?",
  "Où aimez-vous marcher ? Dans un parc, dans votre quartier préféré, dans la forêt ?",
  "Y a-t-il des moments dans votre semaine où vous pourriez marcher au lieu de prendre la voiture ? Quand cela pourrait-il être le cas ?",
  "Les petits changements s'additionnent : lorsque vous vous rendez quelque part en voiture, vous pourriez vous garer un peu plus loin de votre destination, ce qui vous obligerait à marcher davantage.",
  "Les petits changements s'additionnent : si vous ne travaillez de la maison, essayez d'aller voir un collègue au lieu de lui envoyer un courriel et éloignez votre téléphone afin de devoir vous lever pour répondre.",
  "Les petits changements s'additionnent : essayez de prendre les escaliers plutôt que l'ascenseur.",
  "Passez-vous beaucoup de temps devant la télévision ou à regarder votre téléphone ? Après 30 minutes en position assise, levez-vous, étirez-vous et marchez pendant quelques minutes. Voyez comment vous vous sentez après ?",
  "Les membres de la famille qui marchent ensemble sont tous en meilleure santé. Qui aimeriez-vous emmener avec vous ? Votre partenaire, vos enfants, vos parents, vos frères et sœurs ?",
  "Avez-vous des amis ou des membres de votre famille qui sont actifs ? Essayez d'organiser une sortie active avec eux.",
  "N'oubliez pas que faire quelques pas vaut toujours mieux que ne pas en faire du tout.",
  "Nous avons tous des jours où il est plus difficile d'être actif. Ne vous inquiétez pas, c'est normal. Demain sera un nouveau jour.",
  "Vous vous sentez en manque d'énergie ? Notre première réaction est souvent de nous asseoir et de faire moins d'efforts. Cependant, pour beaucoup de gens, une simple promenade de 10 minutes suffit à les aider à se sentir mieux. Essayez et voyez comment vous vous sentez."
]

# French tips for when goals ARE met
FRENCH_TIPS_MET = [
  "Vous êtes sur la bonne voie ! Continuez comme ça.",
  "Bravo. 😊",
  "Vous vous faites bien ça !",
  "Continuez. Vous êtes en train de prendre de nouvelles habitudes de marche.",
  "Félicitations, vous avez atteint votre objectif !",
  "Bravo ! Vous réussissez bien.",
  "Excellent. La persévérance porte ses fruits.",
  "Bon travail ! Votre engagement en faveur de la santé se note.",
  "On voit que vous faites des efforts pour atteindre vos buts.",
  "Bravo ! Vous atteignez vos objectifs."
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
                message_lines.append(f"Vous avez fait plus que le but de la semaine dernière qui était {previous_target} pas par jour.")
            else:
                message_lines.append(f"Vous avez fait moins que le but de la semaine dernière qui était {previous_target} pas par jour.")
        
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
    Returns detailed status - caller handles model updates.
    
    Returns:
        dict: {
            'success': bool,
            'error_message': str or None,
            'subject': str,
            'body': str,
            'timestamp': str (ISO format)
        }
    """
    from django.utils import timezone
    
    timestamp = timezone.now()
    result = {
        'success': False,
        'error_message': None,
        'subject': None,
        'body': None,
        'timestamp': timestamp.isoformat()
    }
    
    try:
        subject, message_body = create_email_content(participant, goal_data)
        result['subject'] = subject
        result['body'] = message_body
        
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'john.dowling@rimuhc.ca')
        recipient_email = participant.user.email
        
        # ✅ Get CC list from settings, or default to empty
        cc_list = getattr(settings, 'GOAL_NOTIFICATION_CC', [])

        try:
            send_mail(
                subject=subject,
                message=message_body,
                from_email=from_email,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            
            # ✅ Send a separate copy to CC addresses if any
            if cc_list:
                send_mail(
                    subject=f"[CC] {subject}",
                    message=message_body,
                    from_email=from_email,
                    recipient_list=cc_list,
                    fail_silently=True,  # don’t break participant emails if CC fails
                )

            result['success'] = True
            logger.info(f"Goal notification sent to {recipient_email} in {participant.language}")
            
        except Exception as email_error:
            result['error_message'] = f"SMTP error: {str(email_error)}"
            logger.warning(f"Email sending failed for {recipient_email}: {result['error_message']}")
        
        return result
        
    except Exception as e:
        result['error_message'] = f"Content creation error: {str(e)}"
        logger.error(f"Failed to create notification for participant {participant.id}: {result['error_message']}")
        return result


def create_message_history_entry(notification_result, goal_data, participant_language):
    """Create message history entry from notification result."""
    return {
        "date": notification_result['timestamp'],
        "subject": notification_result['subject'],
        "content": notification_result['body'],
        "language": participant_language,
        "goal_data": {
            "average_steps": goal_data.get('average_steps'),
            "new_target": goal_data.get('new_target'),
            "target_was_met": goal_data.get('target_was_met')
        },
        "email_sent": notification_result['success'],
        "error_message": notification_result.get('error_message')
    }