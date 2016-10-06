import xlrd
import random
import logging
from sqlalchemy import *
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy.engine.url import URL
from los_db import *

def generate_la_id():
	prefix = "LA"
	same_flag = True
	code = ""
	while same_flag == True:
		num = random.randrange(10000000,99999999)
		code = prefix + str(num)
		sel_code = session.query(exists().where(CustomerDetails.Customer_id == code)).scalar()
		if not sel_code:
			same_flag = False
	return code

# reading MIS data from the Novopay into a data dictionary
# inserting the data in MySQL database
filepath = "/Users/megha/Downloads/MIS_Report_Feb_July_2016.xlsx"
book = xlrd.open_workbook(filepath)
num_sheets = book.nsheets

sheet_names = book.sheet_names()
print sheet_names
sheets = {}

for i in range(0, num_sheets):
	title = "Sheet"+str(i+1)
	sheets[title] = book.sheet_by_index(i)
	table = []
	parts = sheet_names[i].split('_')
	month = parts[0]
	year = parts[1]
	for n in range(2,sheets[title].nrows):
		obj = {}
		for c in range(sheets[title].ncols):
			col_name = sheets[title].cell(1,c).value
			if col_name == "Date of enrollment":
				xdate = xlrd.xldate_as_tuple(sheets[title].cell(n,c).value,book.datemode)
				format_date = str(xdate[0])+"-"+str(xdate[1])+"-"+str(xdate[2])
				obj[col_name+str(c)] = format_date
				print format_date
			else:
				if sheets[title].cell(n,c).value == '':
					obj[col_name+str(c)] = None
				else:
					obj[col_name+str(c)] = sheets[title].cell(n,c).value

		table.append(obj)
		print "Done"
		if(i == 0):
			la_id = generate_la_id()
		
			try:
				los_engine.execute(CustomerDetails.__table__.insert(),\
					Customer_id=la_id, customer_type = "retailer",\
					partner_enrollment_date=obj["Date of enrollment5"])
				los_engine.execute(AlliancePartner.__table__.insert(),\
					Customer_id=la_id,unique_id=obj["Retailer Code1"])
				session.commit()
			except Exception, e:
				session.rollback()
				logging.error("MySQLDB error: "+str(e))
		try:
			los_engine.execute(SalesData.__table__.insert(),\
				retailer_code=obj["Retailer Code1"], month=month, year=year,\
				bill_payment=obj["Bill Payment6"], dth=obj["DTH7"],\
				mobile=obj["Mobile8"], money_transfer=obj["Money transfers9"],\
				other = obj["Others10"], bank_commission=obj["Bank commisions11"],\
				grand_total = obj["Grand Total12"])
			los_engine.execute(TransactionData.__table__.insert(),\
				retailer_code=obj["Retailer Code1"], month=month, year=year,\
				bill_payment=obj["Bill Payment13"], dth=obj["DTH14"],\
				mobile=obj["Mobile15"], money_transfer=obj["Money Transfers16"],\
				other = obj["Others17"], bank_commission=obj["Bank commissions18"],\
				grand_total = obj["Grand Total19"])
			session.commit()
			logging.info("Data inserted successfully!")
		except Exception, e:
			session.rollback()
			logging.error("MySQLDB exception: " +str(e))







		
