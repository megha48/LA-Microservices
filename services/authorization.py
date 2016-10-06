from los_db import *
from sqlalchemy.sql import exists

class authorization:

	def validateAuthorization(self,token):
		result = session_gateway.query(exists().where(tokens.token == token).where(tokens.active == 1)).scalar()
		session_gateway.commit()
		return result