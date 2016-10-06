import sqlalchemy.types
import os
from sqlalchemy import *
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.ext import mutable
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.engine.url import URL

los_base = automap_base()
kyc_base = automap_base()
gateway_base = automap_base()

AWS_IP = os.environ['mysql_host_los']
KYC_HOST_IP = os.environ['mysql_host_kyc']
DB_PORT = os.environ['mysql_port']
MYSQL_USER = os.environ['mysql_user']
MYSQL_PASSWORD = os.environ['mysql_password']
KYC_USER = os.environ['kyc_user']
KYC_PASSWORD=os.environ['kyc_password']
AWS_DB_NAME = os.environ['mysql_db_los']
NG_DB_NAME = os.environ['mysql_db_kyc']
MONGO_HOSTNAME = os.environ['MONGO_HOST'] 
MONGO_PORT = os.environ['MONGO_PORT']
GATEWAY_DB = os.environ['mysql_db_gateway']
GATEWAY_HOST = os.environ['mysql_host_gateway']
# MYSQL_USER = os.envrion['mysql_user']
# MYSQL_PASSWORD = os.envrion['mysql_password']


GATEWAY_DB_URI = {
	'drivername':'mysql',
	'host': GATEWAY_HOST,
	'port': DB_PORT,
	'username': MYSQL_USER,
	'password': MYSQL_PASSWORD,
	'database': GATEWAY_DB
}

KYC_DB_URI = {
	'drivername' : 'mysql',
	'host' : KYC_HOST_IP,
	'port' : DB_PORT,
	'username' : KYC_USER,
	'password' : KYC_PASSWORD,
	'database' : NG_DB_NAME
}

LOS_DB_URI = {
	'drivername' : 'mysql',
	'host' : AWS_IP,
	'port' : DB_PORT,
	'username' : MYSQL_USER,
	'password' : MYSQL_PASSWORD,
	'database' : AWS_DB_NAME
}

kyc_engine = create_engine(URL(**KYC_DB_URI), pool_size=20, pool_recycle=3600)
Session_kyc = sessionmaker(autocommit=False,autoflush=False,bind=kyc_engine)
kyc_base.prepare(kyc_engine, reflect=True)

los_engine = create_engine(URL(**LOS_DB_URI), pool_size=20, pool_recycle=3600)
Session_los = sessionmaker(autocommit=False,autoflush=False,bind=los_engine)
los_base.prepare(los_engine, reflect=True)

gateway_engine = create_engine(URL(**GATEWAY_DB_URI), pool_size=20, pool_recycle=3600)
Session_gateway = sessionmaker(autocommit=False,autoflush=False,bind=gateway_engine)
gateway_base.prepare(gateway_engine, reflect=True)

tokens = gateway_base.classes.tokens

# connecting to tables in KYC engine
customer_ekyc_object = Table('customer_eKYC', MetaData(bind=None), autoload=True, autoload_with=kyc_engine)
customer_ekyc_cols = customer_ekyc_object.columns

# connecting to tables in LOS database
CustomerDetails = los_base.classes.customer_details
CustomerPersonal = los_base.classes.customer_personal
AlliancePartner = los_base.classes.alliance_partner
CustomerLoanInfo = los_base.classes.loan_preference
CustomerLoanMap = los_base.classes.customer_loan_mapping
CustomerKYC = los_base.classes.customer_kyc
SalesData = los_base.classes.mis_sales_data
TransactionData = los_base.classes.mis_transaction_data
DocumentDetails = los_base.classes.document_details
DocumentStatus = los_base.classes.document_upload_status
ProfileCompleteness = los_base.classes.profile_completeness
CustomerState = los_base.classes.customer_state
AuditTable = los_base.classes.audit_tab


# session_ng = Session(kyc_engine)
session = scoped_session(Session_los)
session_ng = scoped_session(Session_kyc)
session_gateway = scoped_session(Session_gateway)


