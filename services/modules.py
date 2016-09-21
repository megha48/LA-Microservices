from field_op_db import *
from los_db import *
from werkzeug.wrappers import Response
from PIL import Image
import logging
import logging.config
import requests
import json
import base64
import urllib, urllib2
import io
import time

# global variable definition
docs_list = {}
reqd_details = ["marital_status", "residence_type", "store_partnership", "partner_share", "monthly_expenses"]
rules = ["Retailer Transaction Data > 3 months", "Retailer Sales in last 3 months > 550000",\
 "Reatiler Vintage > 6 months"]
result = ["Loan Accepted", "Loan Rejected"]

month_map = {
	"01":["january","jan"],
	"02":["february","feb"],
	"03":["march","mar"],
	"04":["april","apr"],
	"05":["may"],
	"06":["june","jun"],
	"07":["july","jul"],
	"08":["august","aug"],
	"09":["september","sep","sept"],
	"10":["october","oct"],
	"11":["november","nov"],
	"12":["december","dec"]
}

def prepare_json_obj(rules):
	# making a scalable decision tree
	rule_inc = 0
	tree_data = []
	decision_payload = {}
	decision_payload["name"] = rules[rule_inc]
	decision_payload["parent"] = None
	decision_payload["children"] = []
	tree_data.append(decision_payload)

	decision_payload = {}
	decision_payload["name"] = result[1]
	decision_payload["parent"] = rules[rule_inc]
	tree_data.append(decision_payload)

	sub_tree = tree_data
	rule_inc=rule_inc+1
	
	while (rule_inc < len(rules)):
		comp = []
		child_obj = {}
		child_obj["name"] = rules[rule_inc]
		child_obj["parent"] = rules[rule_inc-1]
		child_obj["children"] = []
		comp.append(child_obj)

		child_obj = {}
		if rule_inc < len(rules)-1:
			child_obj["name"] = result[1]
		else:
			child_obj["name"] = result[0]
		child_obj["parent"] = rules[rule_inc-1]
		comp.append(child_obj)
		
		temp = sub_tree[0]
		temp["children"] = (comp)
		sub_tree = comp
		rule_inc = rule_inc+1
	return tree_data

decision_map = prepare_json_obj(rules)

def fetch_retailers(field_op_id):
	retailer_list = []
	status_list = []
	try:
		check = session.query(exists().where(RetailerFieldOpMap.field_op_id == field_op_id))
		print check
		if check:
			select_q1 = session.query(RetailerFieldOpMap.retailer_id).filter(RetailerFieldOpMap.field_op_id == field_op_id).all()
			retailer_list = list(select_q1)

			print retailer_list

			if retailer_list:
				try:
					status_list = session.query(RetailerFieldOpMap.state).filter(RetailerFieldOpMap.field_op_id == field_op_id).all()
				finally:
					session.flush()
	except Exception, e:
		logging.error("The query condition is not satisfied")
		message = "MySQLDB error " + str(e)
		print message
	return retailer_list, status_list

def store_customer_details(data):

	form_json = json.load(data.stream)
	message = ""
	response_code = 0

	# extract phone number from from the JSON Payload
	phone_number = form_json["personal_mobile"]
	form_data = {}

	form_data["residence_type"] = form_json["residence_type"]
	form_data["marital_status"] = form_json["marital_status"]
	form_data["store_partnership"] = form_json["store_partnership"]
	form_data["partner_share"] = form_json["partner_share"]
	form_data["num_dependants"] = form_json["num_dependants"]
	form_data["monthly_expenses"] = form_json["monthly_expenses"]

	ext_id = form_json["external_id"]

	form_data = json.dumps(form_data)

	# store the form details in the db
	try:
		engine.execute(LosDetails.__table__.insert(),\
			personal_mobile=phone_number, misc_attributes=form_data, external_id=ext_id)

		# call to be made to update the customer_loan_mapping table once the server is up
		#  external_id to come from the alliance_partner table
		session.commit()
		message = "Successfully stored the loan details"
		response_code = 200
	except Exception,e:
		session.rollback()
		message = "Insertion error: "+str(e)
		response_code = 400
	
	data = {}
	data["msg"] = message
	resp_data = json.dumps(data)

	print str(resp_data)
	resp = Response(resp_data, response_code)
	return resp

def aadhaar_verify_dataext(aadhaar_kyc_info, kyc_data): 
	if "house" in aadhaar_kyc_info["kyc"]["poa"]:
		kyc_data["house"]= aadhaar_kyc_info["kyc"]["poa"]["house"]

	if "vtc" in aadhaar_kyc_info["kyc"]["poa"]:
		kyc_data["vtc"]= aadhaar_kyc_info["kyc"]["poa"]["vtc"]

	if "subdist" in aadhaar_kyc_info["kyc"]["poa"]:
		kyc_data["subdist"]= aadhaar_kyc_info["kyc"]["poa"]["subdist"]

	if "dist" in aadhaar_kyc_info["kyc"]["poa"]:
		kyc_data["dist"]= aadhaar_kyc_info["kyc"]["poa"]["dist"]

	if "state" in aadhaar_kyc_info["kyc"]["poa"]:
		kyc_data["state"]= aadhaar_kyc_info["kyc"]["poa"]["state"]

	if "pc" in aadhaar_kyc_info["kyc"]["poa"]:
		kyc_data["pc"]= aadhaar_kyc_info["kyc"]["poa"]["pc"]

	if "po" in aadhaar_kyc_info["kyc"]["poa"]:
		kyc_data["po"]= aadhaar_kyc_info["kyc"]["poa"]["po"]    

def aadhaar_verify_data(aadhaar_kyc_info, kyc_data):
	kyc_data["name"]=None
	kyc_data["dob"]= None
	kyc_data["gender"]= None
	kyc_data["co"]= None
	kyc_data["house"]= None
	kyc_data["vtc"]= None
	kyc_data["subdist"]= None
	kyc_data["dist"]= None
	kyc_data["state"]= None
	kyc_data["pc"]= None
	kyc_data["po"]= None
	kyc_data["aadhaar_id"]= None
	
	if "name" in aadhaar_kyc_info["kyc"]["poi"]:
		kyc_data["name"]= aadhaar_kyc_info["kyc"]["poi"]["name"]

	if "dob" in aadhaar_kyc_info["kyc"]["poi"]:
		kyc_data["dob"]= aadhaar_kyc_info["kyc"]["poi"]["dob"]

	if "gender" in aadhaar_kyc_info["kyc"]["poi"]:
		kyc_data["gender"]= aadhaar_kyc_info["kyc"]["poi"]["gender"]

	if "co" in aadhaar_kyc_info["kyc"]["poa"]:
		kyc_data["co"]= aadhaar_kyc_info["kyc"]["poa"]["co"]

	aadhaar_verify_dataext(aadhaar_kyc_info, kyc_data)
							
def aadhaar_verify_inserdata(customer_count, kyc_data, file_id, aadhaar_no, customer_id, aadhaar_kyc_info):
	if customer_count ==0 : 
		try:
			stmt = customer_ekyc_object.insert().\
			values({'Customer_id': customer_id, 'name': kyc_data["name"], 'dob': kyc_data["dob"],
			'gender': kyc_data["gender"], 'co': kyc_data["co"], 'house': kyc_data["house"],
			"vtc":kyc_data["vtc"], "subdist": kyc_data["subdist"], "dist": kyc_data["dist"], "state": kyc_data["state"],
			"pc":kyc_data["pc"], "po":kyc_data["po"], "aadhaar_id":aadhaar_no, "photo_file_object": str(file_id) })
			session_ng.execute(stmt)
			session_ng.commit()

		except Exception,e:
			logging.error("aadhaar_otp_verify: Unable to insert customer Aadhaar data")
			logging.error(msg=e)
			status_code= 511
			data= {"message":"Unable to do eKYC. Please try again", "status":status_code, "content_type": 'application/json'}
			data_json= json.dumps(data)
			resp= Response(data_json, 500)
			h= resp.headers
			h['Access-Control-Allow-Origin'] = "*"
			h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
			h['Access-Control-Allow-Methods']= "GET, POST, PUT"
			return resp
	else:
		try:
			stmt = customer_ekyc_object.update().\
			where(customer_ekyc_cols['Customer_id'] == customer_id).\
			values({'Customer_id': customer_id, 'name': kyc_data["name"], 'dob': kyc_data["dob"],
			'gender': kyc_data["gender"], 'co': kyc_data["co"], 'house': kyc_data["house"],
			"vtc":kyc_data["vtc"], "subdist": kyc_data["subdist"], "dist": kyc_data["dist"], "state": kyc_data["state"],
			"pc":kyc_data["pc"], "po":kyc_data["po"], "aadhaar_id":aadhaar_no, "photo_file_object": str(file_id) })
			session_ng.execute(stmt)
			session_ng.commit()

		except Exception,e:
			logging.error("aadhaar_otp_verify: Unable to update customer Aadhaar data")
			logging.error(msg=e)
			status_code= 511
			data= {"message":"Unable to do eKYC. Please try again", "status":status_code, "content_type": 'application/json'}
			data_json= json.dumps(data)
			resp= Response(data_json, 500)
			h= resp.headers
			h['Access-Control-Allow-Origin'] = "*"
			h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
			h['Access-Control-Allow-Methods']= "GET, POST, PUT"
			return resp
	
	status_code= 201
	aadhaar_info= json.dumps(aadhaar_kyc_info)
	data= {"message":"KYC done successfully", "status":status_code, "aadhaar_info":aadhaar_kyc_info, "content_type": 'application/json'}
	data_json= json.dumps(data)
	logging.debug(msg= data_json)

	resp= Response(data_json, 200)
	h= resp.headers
	h['Access-Control-Allow-Origin'] = "*"
	h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
	h['Access-Control-Allow-Methods']= "GET, POST, PUT"
	return resp

def aadhaar_verify_info(aadhaar_kyc_info, customer_id, aadhaar_no):
	# storing the KYC information
	logging.debug(msg= "aadhaar_otp_verify: kyc info success")
	print aadhaar_kyc_info["kyc"]["photo"]
	photo= base64.b64decode(aadhaar_kyc_info["kyc"]["photo"])

	image = Image.open(io.BytesIO(photo))

	print image
	
	# r_image= aadhaar_verify_uploadimage(photo, customer_id)
	# r= json.loads(r_image.data)
	# if r["status"]==521:
	# 	return r_image

	# file_id= r["file_id"]
	# print file_id

	file_id = None
	
	# Customer EKYC Object
	try: 
		customer_count= session_ng.query(customer_ekyc_object).filter(customer_ekyc_cols["Customer_id"]==customer_id).count()
		kyc_data= {}
		aadhaar_verify_data(aadhaar_kyc_info, kyc_data)
		return aadhaar_verify_inserdata(customer_count, kyc_data, file_id, aadhaar_no, customer_id, aadhaar_kyc_info)
		
	except Exception,e:
		logging.error("aadhaar_otp_verify: Error creating/updating EKYC object")
		logging.error(msg=e)
		status_code = 511
		data= {"message":"Unable to do eKYC. Please try again", "status":status_code, "content_type": 'application/json'}
		data_json= json.dumps(data)
		resp= Response(data_json, 500)
		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
		return resp  

def store_kyc(data):
	kyc_data = data.stream.read()
	print kyc_data

	kyc_json = json.loads(kyc_data)
	aadhaar_no = int(kyc_json["aadhaar-id"])
	customer_id = 'DLC344'
	return aadhaar_verify_info(kyc_json,customer_id,aadhaar_no)

def execute_rule1(retailer_code, edate):

	# parsing the date
	date_parts = edate.split('-')
	days = int(date_parts[2])
	month = int(date_parts[1])
	month_name = month_map[str(date_parts[1])]
	year = int(date_parts[0])

	txn_data = session.query(TransactionData).filter(TransactionData.external_id==retailer_code).all()
	cnt_txn = 0
	if year < 2016 or (month < 2 and year == 2016):
		print "in old"
		for txn in txn_data:
			if cnt_txn < 3:
				if txn.grand_total > 0:
					cnt_txn = cnt_txn + 1
					print txn.grand_total
		if cnt_txn == 3:
			print "Yes for Transaction Data"
			return True
	else:
		print "in new"
		for i in range(month,len(txn_data)+1):
			if cnt_txn < 3:
				if txn.grand_total > 0:
					cnt_txn = cnt_txn + 1
		if cnt_txn == 3:
			print "Yes for Transaction Data"
			return True
	return False

def execute_rule2(rcode, edate):

	# parsing the date
	date_parts = edate.split('-')
	days = int(date_parts[2])
	month = int(date_parts[1])
	year = int(date_parts[0])

	sales_data = session.query(SalesData).filter(SalesData.external_id==rcode).all()
	sales_amount = 0
	cnt_txn = 0
	if year < 2016 or (month < 2 and year == 2016):
		print "in old"
		for txn in sales_data:
			if cnt_txn < 3 and sales_amount < 550000:
				if txn.grand_total > 0:
					cnt_txn = cnt_txn + 1
					sales_amount = sales_amount + txn.grand_total
					print sales_amount
		if sales_amount > 550000:
			print("Yes for Sales>5.5L")
			return True
	else:
		print "in new"
		for i in range(month,len(sales_data)+1):
			if cnt_txn < 3 and sales_amount < 550000:
				if txn.grand_total > 0:
					cnt_txn = cnt_txn + 1
					sales_amount = sales_amount+txn.grand_total
		if sales_amount > 550000:
			print("Yes for Sales>5.5L")
			return True
	return False

def execute_rule3(edate):

	# parsing the date field
	print edate
	parts = edate.split('-')
	days = int(parts[2])
	month = int(parts[1])
	year = int(parts[0])

	if year < 2016 or (month < 2 and year == 2016):
		print "in old"
		print "Yes for Retailer Vintage"
		return True
	else:
		print "in new"
		total_days = days
		current_date = time.strftime("%d-%m-%y")
		current_days = int(current_date.split('-')[0])
		current_month = int(current_date.split('-')[1])
		current_year = int(current_date.split('-')[2])
		if current_year > year:
			print "Yes for Retailer Vintage"
			return True
		else:
			if current_month > month:
				diff = current_month - month
				approx_days = diff*30
		total_days = total_days + approx_days
		print total_days
		if total_days > 180:
			print "Yes for Retailer Vintage"
			return True
	return False

# to be invoked once the loan has been disbursed to the customer
def create_and_store_client(url_link, input_params):
	# get request
	# params = urllib.urlencode(input_params)
	# url = url_link+"?"+params
	# response = urllib2.urlopen(url)
	# print response.info()

	# post request
	result = requests.get(url_link, data=input_params)
	data = result.text
	print data

def rule_based_filtering(la_id):
	check_id = session.query(exists().where(MISData.loansapp_id==la_id)).scalar()
	if check_id:
		retailer_code, enroll_date = session.query(MISData.external_id, MISData.enrollment_date).\
			filter(MISData.loansapp_id==la_id).first()
		enroll_date = str(enroll_date)

		dmap = decision_map
		obj1 = dmap[0]
		obj2 = dmap[1]

		if execute_rule1(retailer_code, enroll_date) == True:
			obj1["result"] = "success"
			temp = obj1["children"]
			sub_obj1 = temp[0]
			sub_obj2 = temp[1]
			obj1["children"] = []
			if execute_rule2(retailer_code, enroll_date) == True:
				sub_obj1["result"] = "success"
				sub_temp = sub_obj1["children"]
				sub_sub_obj1 = sub_temp[0]
				sub_sub_obj2 = sub_temp[1]
				sub_obj1["children"] = []
				if execute_rule3(enroll_date) == True:
					sub_sub_obj1["result"] = "success"
				else:
					sub_sub_obj2["result"] = "failed"
				sub_obj1["children"].append(sub_sub_obj1)
				sub_obj1["children"].append(sub_sub_obj2)
			else:
				sub_obj2["result"] = "failed"
			obj1["children"].append(sub_obj1)
			obj1["children"].append(sub_obj2)
		else:
			obj2["result"] = "failed"
		dmap.append(obj1)
		dmap.append(obj2)
		print dmap
		return dmap
	message = "Loansapp ID does not exist"
	return message


def filter_customers(la_id):
	message = ""
	if len(la_id) is not 10:
		message = "Invalid ID entered. Please check credentials."
	else:
		message = rule_based_filtering(la_id)
	return message


input_data = {}
input_data["firstname"] = "Megha"
input_data["lastname"] = "Vij"
input_data["gender"] = "Female"
input_data["mobileNo"] = "9888383786"
input_data["externalId"] = "NP123"
input_data["activationDate"] = "16 September 2016"
input_data["submittedOnDate"] = "16 September 2016"
input_data["dateOfBirth"] = "04 August 1991"

# create_and_store_client("http://lend.ml:4060/LoansApp/API/v1/createClient",input_data)

