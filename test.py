import jwt

# Exemple simple
token = jwt.encode({'test': 'ok'}, 'secret', algorithm='HS256')
decoded = jwt.decode(token, 'secret', algorithms=['HS256'])
print(decoded)
