import uuid

def regenerate_fitbit_token(participant):
    participant.fitbit_auth_token = uuid.uuid4()  # assign a UUID object
    participant.save()
    return str(participant.fitbit_auth_token)   # return string form if needed
