import sqlalchemy.types
from sqlalchemy import *
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.ext import mutable
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL

los_base = automap_base()

KYC_DB_URI = {
	'drivername' : 'mysql',
	'host' : '103.230.86.11',
	'port' : '3306',
	'username' : 'root',
	'password' : 'root',
	'database' : 'dlc'
}

LOS_DB_URI = {
	'drivername' : 'mysql',
	'host' : 'localhost',
	'port' : '4080',
	'username' : 'root',
	'password' : 'admin@sql',
	'database' : 'los_schema'
}

kyc_engine = create_engine(URL(**KYC_DB_URI))
los_base.prepare(kyc_engine, reflect=True)

los_engine = create_engine(URL(**LOS_DB_URI))
los_base.prepare(los_engine, reflect=True)

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

session_ng = Session(kyc_engine)
session = Session(los_engine)


