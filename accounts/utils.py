# # accounts/utils.py
# def jwt_payload_handler(user):
#     return {
#         'user_id': user.id,
#         'username': user.username,
#         'email': user.email,
#         'exp': datetime.datetime.utcnow() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
#     }