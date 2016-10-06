import xlrd
import datetime
import logging
from los_db import *


path_personal_info = '/Users/megha/Documents/FOS/CustomerPersonalInfo.xlsx'
path_checklist = '/Users/megha/Documents/FOS/ChecklistDocuments.xlsx'

def read_basic_info_sheet(filepath):
	info_book = xlrd.open_workbook(filepath)

	info_sheet_names = info_book.sheet_names()
	print info_sheet_names
	sheets = {}

	sheets[info_sheet_names[0]] = info_book.sheet_by_index(0)
	field_vals = {}

	map_db_fields = {}
	db_names = ["title","first_name","last_name", "novopay_mobile","father_name","mother_maiden_name","account_title","gender","date_of_birth",\
	"permanent_address","current_address","email_address","country","residential_status","nationality","annual_income","mobile_no","PAN_no","document_id_addr",\
	"occupation","marital_status","no_of_children","no_of_dependents","duration_current_residence_months","proprietorship_share"]

	for i in range(3,sheets[info_sheet_names[0]].nrows):
		row_name  = sheets[info_sheet_names[0]].cell(i,1).value
		row_name = row_name.rstrip()
		print row_name
		if sheets[info_sheet_names[0]].cell(i,2).value != '':
			if row_name == "Date Of Birth":
				row_val = sheets[info_sheet_names[0]].cell(i,2).value
				xdate = xlrd.xldate_as_tuple(row_val, info_book.datemode)
				format_date = str(xdate[0])+"-"+str(xdate[1])+"-"+str(xdate[2])
				field_vals[row_name] = format_date
			else:
				row_val = sheets[info_sheet_names[0]].cell(i,2).value
				if row_val == '':
					row_val = 0
				field_vals[row_name] = row_val
		if i < len(db_names)+3:
			map_db_fields[row_name] = db_names[i-3]
	print field_vals
	return field_vals, map_db_fields


def read_checklist_sheet(filepath):
	
	doc_chklist = xlrd.open_workbook(filepath)

	sheet_names = doc_chklist.sheet_names()
	num_sheets = doc_chklist.nsheets
	sheet = {}

	for i in range(0, num_sheets):
		title = "Sheet"+str(i+1)
		sheet[title] = doc_chklist.sheet_by_index(i)
		retailer_list = sheet[title].row_values(1)

		num_rows = sheet[title].nrows
		row_names = []

		for j in range(1,num_rows):
			row_name = sheet[title].cell(j,0).value
			row_names.append(row_name)

		retailer_checklist = {}

		for k in range(1,2):
			checklist = []
			for l in range(2,num_rows):
				checklist.append(row_names[l-1]+":"+sheet[title].cell(l,k).value)
			retailer_checklist[retailer_list[k]] = checklist
		print retailer_checklist
	return retailer_checklist


def update_doc_status(retailer_checklist):
	doc_pairs = {}
	try:
		doc_ids = session.query(DocumentDetails.doc_id).all()
		doc_names = session.query(DocumentDetails.doc_name).all()

		for i in range(len(doc_ids)):
			doc_pairs[doc_names[i][0]] = doc_ids[i][0]
	except Exception, e:
		print "Error in retrieving document details from DB: "+ str(e)
	retailer_ids = retailer_checklist.keys()
	
	try:
		retailer_id = retailer_ids[0]
		print retailer_id
		customer_id = session.query(AlliancePartner.Customer_id).filter(AlliancePartner.unique_id==retailer_id).first()
		customer_id = customer_id[0]
		list_docs = retailer_checklist[retailer_id]

		for doc in list_docs:
			collection_status=0
			dparts = doc.split(':')
			dparts[1] = dparts[1].lower()
			cust_exists = session.query(exists().where(CustomerKYC.Customer_id==customer_id)).scalar()

			if dparts[1] == 'y' or dparts[1] == 'yes':
				collection_status = 1
			elif dparts[1] == 'n' or dparts[1] == 'no':
				collection_status = 0

			try:
				if doc.startswith("KYC - POI"):
					print cust_exists
					if cust_exists:
						session.query(CustomerKYC).with_lockmode('update').\
						filter(CustomerDetails.Customer_id == customer_id).\
						update({"id_proof_flag":collection_status},synchronize_session='fetch')
					else:
						los_engine.execute(CustomerKYC.__table__.insert(),\
							Customer_id = customer_id, id_proof_flag=collection_status)
					session.commit()
				elif doc.startswith("KYC - POA"):
					print cust_exists
					if cust_exists:
						session.query(CustomerKYC).with_lockmode('update').\
						filter(CustomerDetails.Customer_id == customer_id).\
						update({"address_proof_flag":collection_status}, synchronize_session='fetch')
					else:
						los_engine.execute(CustomerKYC.__table__.insert(),\
							Customer_id = customer_id, address_proof_flag=collection_status)
					session.commit()
				else:
					docID = doc_pairs[dparts[0]]
					los_engine.execute(DocumentStatus.__table__.insert(),\
					Customer_id=customer_id, doc_id = docID, collect_flag=collection_status)
					session.commit()

				cust_check = session.query(exists().where(ProfileCompleteness.Customer_id==customer_id)).scalar()
				if cust_check:
					logging.debug("Updating Customer Status for Document status")
					session.query(ProfileCompleteness).with_lockmode('update').\
						filter(CustomerPersonal.Customer_id==customer_id).\
						update({"kyc_verification_flag":1, "financial_proofs_flag":1},\
						 synchronize_session='fetch')
				else:
					logging.debug("Inserting status of Documents collected: "+customer_id)
					los_engine.execute(ProfileCompleteness.__table__.insert(),\
						Customer_id = customer_id, kyc_verification_flag=1, financial_proofs_flag=1)
			except Exception, e:
				session.rollback()
				print "Error in inserting Document Status in DB: "+str(e)
	except Exception, select_e:
		session.rollback()
		print "Error in fetching the document details: "+str(select_e)


def store_basic_info(db_fields, form_fields):
	retailer_mobile = ""
	if form_fields["Novopay Mobile Number"]:
		retailer_mobile = form_fields["Novopay Mobile Number"]
		check_retailer = session.query(exists().where(CustomerDetails.mobile_no==retailer_mobile)).scalar()

		if check_retailer:
			customer_id = session.query(CustomerDetails.Customer_id).filter(CustomerDetails.mobile_no==retailer_mobile).first()
			cid = customer_id[0]

			try:
				logging.debug("Updating the basic information for customer: "+cid)
				if int(form_fields["Proprietor Share"]) != 0:
					session.query(CustomerDetails).with_lockmode('update').\
						filter(CustomerDetails.Customer_id==cid).\
						update({"first_name":form_fields["First Name"], "last_name": form_fields["Last Name"],\
						"date_of_birth":form_fields["Date Of Birth"], "email_address":form_fields["E Mail ID"],\
					 	"mobile_no":form_fields["Mobile No"], "proprietorship_flag":1,"proprietorship_share":form_fields["Proprietor Share"]}, \
					 	synchronize_session='fetch')
				else:
					session.query(CustomerDetails).with_lockmode('update').\
						filter(CustomerDetails.Customer_id==cid).\
						update({"first_name":form_fields["First Name"], "last_name": form_fields["Last Name"],\
						"date_of_birth":form_fields["Date Of Birth"], "email_address":form_fields["E Mail ID"],\
					 	"mobile_no":form_fields["Mobile No"], "proprietorship_flag":0,"proprietorship_share":form_fields["Proprietor Share"]},\
					 	synchronize_session='fetch')

				cust_check = session.query(exists().where(CustomerPersonal.Customer_id==cid)).scalar()
				if cust_check:
					logging.debug("Updating personal information for customer: "+cid)
					session.query(CustomerPersonal).with_lockmode('update').\
						filter(CustomerPersonal.Customer_id==cid).\
						update({"father_name":form_fields["Father Name"], "mother_maiden_name":form_fields["Mother Maiden Name"],\
						"gender":form_fields["Gender"], "permanent_address":form_fields["Permanent Address"],\
						"communication_address":form_fields["Communication Address"], "residential_status":form_fields["Residential Status"],\
						"nationality":form_fields["Nationality"],"occupation":form_fields["Occupation"],"duration_current_residence_months":form_fields["Duration of Stay at Current Residence (months)"],\
						"PAN_no": form_fields["Pan card No"], "annual_income":form_fields["Annual Income"], "marital_status":form_fields["Marital Status"],\
						"no_of_dependents":form_fields["Number of Dependents"], "no_of_children":form_fields["Number of Children"]},\
						 synchronize_session='fetch')
				else:
					logging.debug("Inserting basic information for customer: "+cid)
					los_engine.execute(CustomerPersonal.__table__.insert(),\
						Customer_id = cid,\
						father_name=form_fields["Father Name"],mother_maiden_name=form_fields["Mother Maiden Name"],\
						gender=form_fields["Gender"], permanent_address=form_fields["Permanent Address"],\
						communication_address=form_fields["Communication Address"], residential_status=form_fields["Residential Status"],\
						nationality=form_fields["Nationality"], occupation=form_fields["Occupation"], PAN_no= form_fields["Pan card No"],\
						annual_income=form_fields["Annual Income"],duration_current_residence_months=form_fields["Duration of Stay at Current Residence (months)"],\
						no_of_dependents=form_fields["Number of Dependents"], no_of_children=form_fields["Number of Children"])
				session.commit()
				logging.debug("Insertion successful for customer_details and customer_personal tables")

				cust_check = session.query(exists().where(ProfileCompleteness.Customer_id==cid)).scalar()
				if cust_check:
					logging.debug("Updating Customer Status for Basic Info")
					session.query(ProfileCompleteness).with_lockmode('update').\
						filter(CustomerPersonal.Customer_id==cid).\
						update({"basic_details_flag":1, "download_app_flag":1, "loan_details_flag":1,\
						"create_account_flag":1}, synchronize_session='fetch')
				else:
					logging.debug("Inserting basic information for customer: "+cid)
					los_engine.execute(ProfileCompleteness.__table__.insert(),\
						Customer_id = cid, basic_details_flag=1, download_app_flag=1, loan_details_flag=1, create_account_flag=1)


			except Exception, e:
				session.rollback()
				logging.error("Error in Insertion of Customer Details: "+str(e))
	else:
		logging.warn("The Novopay mobile number has not been provided")


# [vals, map_db] = read_basic_info_sheet(path_personal_info)
# store_basic_info(map_db, vals)


retailer_checks = read_checklist_sheet(path_checklist)
update_doc_status(retailer_checks)



