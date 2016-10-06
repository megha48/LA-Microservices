import xlrd
from los_db import *
import random

chosen_ids = ['KA1RM00071', 'MH1RM00112', 'TL1RM00305', 'MH2RM00048', 'KA1RM00478','619810111695',\
	'10109682','616710110495', '10024956','10034268', '620210111800', '620410111881']

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

# filepath = "/Users/megha/Downloads/DummyData.xlsx"
# book = xlrd.open_workbook(filepath)
# num_sheets = book.nsheets

# sheet_names = book.sheet_names()
# print sheet_names
# sheets = {}

# for i in range(0, num_sheets):
# 	title = "Sheet"+str(i+1)
# 	sheets[title] = book.sheet_by_index(i)
# 	col_names = sheets[title].row_values(1)

# 	print sheets[title].nrows

# 	for j in range(2, sheets[title].nrows):
# 		name = sheets[title].cell(j,0).value
# 		print name
# 		lms_client_id = sheets[title].cell(j,1).value
# 		mobile_no = sheets[title].cell(j,2).value

# 		if len(name.split()) > 1:
# 			fname = name.split()[0]
# 			lname = name.split()[1]
# 		else:
# 			fname = name
# 			lname = None

# 		try:
# 			print chosen_ids[j-2]
# 			customer_id = session.query(AlliancePartner.Customer_id).filter(AlliancePartner.unique_id == chosen_ids[j-2]).first()
# 			customer_id = customer_id[0]
# 			session.query(CustomerDetails).with_lockmode('update').\
# 				filter(CustomerDetails.Customer_id == customer_id).\
# 				update({"first_name":fname,"last_name":lname,"mobile_no":mobile_no})
# 			los_engine.execute(CustomerLoanMap.__table__.insert(),\
# 				Customer_id = customer_id, client_id = lms_client_id, loan_id=1)
# 			session.commit()
# 		except Exception, e:
# 			session.rollback()
# 			print("MySQLDB error:"+str(e))

def add_entry_db(retailer_code,lms_client_id,mobile_no,fname,lname,dob):
	try:
		customer_id = session.query(AlliancePartner.Customer_id).filter(AlliancePartner.unique_id == retailer_code).first()
		session.commit()
		if customer_id:
			customer_id = customer_id[0]

			session.query(CustomerDetails).with_lockmode('update').\
				filter(CustomerDetails.Customer_id == customer_id).\
				update({"first_name":fname,"last_name":lname,"mobile_no":mobile_no,"date_of_birth":dob})
			session.commit()
			los_engine.execute(CustomerLoanMap.__table__.insert(),\
				Customer_id = customer_id, client_id = lms_client_id, loan_id=1)
			session.commit()
		else:
			customer_id = generate_la_id()
			los_engine.execute(CustomerDetails.__table__.insert(),\
				Customer_id=customer_id, mobile_no=mobile_no, first_name=fname,last_name=lname, date_of_birth=dob)
			session.commit()
			los_engine.execute(AlliancePartner.__table__.insert(),\
				Customer_id=customer_id, unique_id=retailer_code)
			session.commit()
			los_engine.execute(CustomerLoanMap.__table__.insert(),\
				Customer_id = customer_id, client_id = lms_client_id, loan_id=1)
			session.commit()
	except Exception, e:
		session.rollback()
		print("MySQLDB error:"+str(e))

# add_entry_db('10001320',82,'9916902830','ABC','Consultants','1979-09-24')
# add_entry_db('10044660', 83, '9878653220', 'Tom', 'Harry', '1998-02-12')
# add_entry_db('1002344552121', 84, '8123094560', 'Vijay', 'Raajaa', '1990-01-11')
add_entry_db('615410109949', 85, '8877234123', 'Luke', 'Patel', '1969-09-24')
# add_entry_db('R0000224',81,'9148195692','Srikanth','Nadhamuni')
