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


base = automap_base()

DB_URI = {
	'drivername' : 'mysql',
	'host' : 'localhost',
	'port' : '4080',
	'username' : 'root',
	'password' : 'admin@sql',
	'database' : 'field_op_db'
}

engine = create_engine(URL(**DB_URI))
base.prepare(engine, reflect=True)

LosDetails = base.classes.customer_mapping
AlliancePartner = base.classes.alliance_partner
CustomerLoanMap = base.classes.customer_loan_mapping

# Field Op data
RetailerFieldOpMap = base.classes.retailer_fieldop_mapping
FieldOpTable = base.classes.field_op_details
StageComments = base.classes.stage_comments
StageCompleteness = base.classes.stage_completeness_stats
StageDetails = base.classes.stage_details
StageScheduler = base.classes.stage_scheduler
StageSubstageMap = base.classes.stage_substage_mapping
CustomerTable = base.classes.customer_details
DocumentTable = base.classes.document_details
DocumentUploader = base.classes.document_upload_tracker

# Novopay Data
MISData = base.classes.customer_mis_data
SalesData = base.classes.sales_data
TransactionData = base.classes.transaction_data

session = Session(engine)