from flask import Blueprint, request
from backend.models import User, Query
from backend.maps.utils import get_deviation_points
from backend import db
import json

webhooks = Blueprint('webhooks', __name__)


@webhooks.route('/incoming', methods=['POST'])
def get_webhook_request():
    request_json = request.get_json()

    print(request_json)

    intent = request_json['queryResult']['intent']['displayName']
    session_id = request_json['session']

    cat_to_num_dict = {
        'food': 1,
        'entertainment': 2,
        'clothing': 3,
        'bills': 4,
        'family': 5,
        'transportation': 6,
        'appliances': 7,
        'miscellaneous': 8
    }

    if intent == "Log In Prompt":
        email = request_json['queryResult']['parameters']['Email']
        user = User.query.filter_by(email=email).first()
        if user is None:
            message = "The user is not registered."
        else:
            user.slack_session = session_id
            db.session.commit()
            message = f"Welcome {user.name}! How can we help you?"

    elif intent == "Initial Input":
        user = User.query.filter_by(slack_session=session_id).first()
        if user is None:
            message = "Please log in."
        else:
            start = request_json['queryResult']['parameters']['Start']
            end = request_json['queryResult']['parameters']['End']
            new_query = Query(entry_o=start, entry_d=end, user_id=user.id)
            db.session.add(new_query)
            db.session.commit()
            message = get_health_message("Query created successfully - calculating ideal stopovers" +
                                         " - please check again in a bit for results")

    elif intent == "Last Result":
        user = User.query.filter_by(slack_session=session_id).first()
        if user is None:
            message = "The user is not registered."
        else:
            last_query = Query.query.filter_by(user_id=user.id).order_by('-id')[0]
            deviations = get_deviation_points(last_query.id)
            message = ', '.join([x['name'] for x in deviations])
            message = f"Suggested stopovers: {message}"

    else:
        message = "I am sorry, I did not get that."

    final_dict = {
        'fulfillmentText': message,
        'payload': {
            'google': {
                "expectUserResponse": True,
                "richResponse": {
                    "items": [
                        {
                            "simpleResponse": {
                                "textToSpeech": message,
                                "displayText": message
                            }
                        }
                    ]
                }
            },
            'facebook': {
                'text': message
            },
            'slack': {
                'text': message
            }
        },
    }

    print(final_dict)

    return json.dumps(final_dict)