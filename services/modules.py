from los_db import *
from werkzeug.wrappers import Response
from PIL import Image
from status_codes import *
from OTP_Settings import *
from datetime import date
import logging
import logging.config
import requests
import json
import base64
import urllib, urllib2
import io
import time
import random
import re

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


# prepare dendogram skeleton
def prepare_dendogram_struct():
	dendogram = {
		"links": [
		{
		  "source": "Scored",
		  "target": "Awaiting",
		  "value": ""
		},
		{
		  "source": "Scored",
		  "target": "Approved",
		  "value": ""
		},
		{
		  "source": "Scored",
		  "target": "Rejected",
		  "value": ""
		},
		{
		  "source": "Approved",
		  "target": "Disbursed",
		  "value": ""
		}
		],
		"nodes": [
		{
		  "node": 1,
		  "name": "Scored",
		  "xPos": 0,
		  "colour": "#DFE378"
		},
		{
		  "node": 2,
		  "name": "Awaiting",
		  "xPos": 1,
		  "colour": "#E37878"
		},
		{
		  "node": 3,
		  "name": "Approved",
		  "xPos": 1,
		  "colour": "#E3BE78"
		},
		{
		  "node":4,
		  "name": "Rejected",
		  "xPos": 1,
		  "colour": "grey"
		},
		{
		  "node":5,
		  "name": "Disbursed",
		  "xPos": 2,
		  "colour": "#78E37C"
		},
		{
		  "node":6,
		  "name": "Currently Scoring",
		  "xPos": 0,
		  "colour": "#7886E3"
		},
		{
		  "node":7,
		  "name": "Not Scored",
		  "xPos": 0,
		  "colour": "#78BEE3"
		}
		],
		"extra_nodes": [
		{
		  "node_name":"Currently Scoring",
		  "value":50
		},
		{
		  "node_name":"Not Scored",
		  "value":50
		}
	]
	}
	return dendogram

# preparing the skeleton of the decision tree
def prepare_json_obj(rules):
	# making a scalable decision tree
	rule_inc = 0
	tree_data = []
	decision_payload = {}
	decision_payload["name"] = rules[rule_inc]
	decision_payload["parent"] = None
	decision_payload["children"] = []
	tree_data.append(decision_payload)

	# decision_payload = {}
	# decision_payload["name"] = result[1]
	# decision_payload["parent"] = rules[rule_inc]
	# tree_data.append(decision_payload)

	sub_tree = tree_data
	rule_inc=rule_inc+1
	
	while (rule_inc < len(rules)+1):
		comp = []
		if rule_inc < len(rules):
			child_obj = {}
			child_obj["name"] = rules[rule_inc]
			child_obj["parent"] = rules[rule_inc-1]
			child_obj["children"] = []
			comp.append(child_obj)

			child_obj = {}
			child_obj["name"] = result[1]
			child_obj["parent"] = rules[rule_inc-1]
			comp.append(child_obj)
		else:
			child_obj = {}
			child_obj["name"] = result[0]
			child_obj["parent"] = rules[rule_inc-1]
			comp.append(child_obj)

			child_obj = {}
			child_obj["name"] = result[1]
			child_obj["parent"] = rules[rule_inc-1]
			comp.append(child_obj)

		temp = sub_tree[0]
		temp["children"] = (comp)
		sub_tree = comp
		rule_inc = rule_inc+1
	return tree_data

decision_map = prepare_json_obj(rules)
# print decision_map

# to retrieve the retailers' list for the loan officer on the home screen
def fetch_retailers(field_op_id):
	retailer_list = []
	status_list = []
	try:
		check = session.query(exists().where(RetailerFieldOpMap.field_op_id == field_op_id))
		if check:
			select_q1 = session.query(RetailerFieldOpMap.retailer_id).filter(RetailerFieldOpMap.field_op_id == field_op_id).all()
			retailer_list = list(select_q1)
			if retailer_list:
				try:
					status_list = session.query(RetailerFieldOpMap.state).filter(RetailerFieldOpMap.field_op_id == field_op_id).all()
				finally:
					session.flush()
			message = "Successful Request"
			logging.debug("Fetched the list of retailers")
	except Exception, e:
		session.rollback()
		logging.error("The query condition is not satisfied")
		message = "MySQLDB error " + str(e)
	return message,retailer_list, status_list

# to store the details filled by a direct customer/retailer in the Loansapp form Activity
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
			session.rollback()
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
	# print aadhaar_kyc_info["kyc"]["photo"]
	photo= base64.b64decode(aadhaar_kyc_info["kyc"]["photo"])

	image = Image.open(io.BytesIO(photo))

	# print image
	
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
		session.rollback()
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

	kyc_json = json.loads(kyc_data)
	aadhaar_no = int(kyc_json["aadhaar-id"])
	# to be added as a parameter in the app
	customer_id = fetch_customer_id(key, val)
	return aadhaar_verify_info(kyc_json,customer_id,aadhaar_no)

def execute_rule1(rid, edate):

	# parsing the date
	date_parts = edate.split('-')
	days = int(date_parts[2])
	month = int(date_parts[1])
	month_name = month_map[str(date_parts[1])]
	year = int(date_parts[0])

	txn_data = session.query(TransactionData).filter(TransactionData.retailer_code == rid).all()
	if txn_data:
		cnt_txn = 0
		if year < 2016 or (month < 2 and year == 2016):
			for txn in txn_data:
				if cnt_txn < 3:
					if txn.grand_total > 0:
						cnt_txn = cnt_txn + 1
			if cnt_txn == 3:
				return True
		else:
			idx = 0
			for i in range(len(txn_data)):
				if txn_data[i].month.lower() in month_name:
					idx = i
					break
			for i in range(idx,len(txn_data)):
				if cnt_txn < 3:
					if txn_data[i].grand_total > 0:
						cnt_txn = cnt_txn + 1
			if cnt_txn == 3:
				return True
	else:
		logging.error("Retailer ID not found in Transaction Table")
	return False

def execute_rule2(rid, edate):

	# parsing the date
	date_parts = edate.split('-')
	days = int(date_parts[2])
	month = int(date_parts[1])
	month_name = month_map[str(date_parts[1])]
	year = int(date_parts[0])

	sales_data = session.query(SalesData).filter(SalesData.retailer_code == rid).all()
	sales_amount = 0.0
	cnt_txn = 0
	if sales_data:
		if year < 2016 or (month < 2 and year == 2016):
			for txn in sales_data:
				if cnt_txn < 3 and sales_amount < 550000:
					if txn.grand_total > 0:
						cnt_txn = cnt_txn + 1
						sales_amount = sales_amount + float(txn.grand_total)
			if sales_amount > 550000:
				return True
		else:
			idx = 0
			for i in range(len(sales_data)):
				if sales_data[i].month.lower() in month_name:
					idx = i
					break
			for i in range(idx,len(sales_data)):
				if cnt_txn < 3:
					if sales_data[i].grand_total > 0:
						cnt_txn = cnt_txn + 1
						sales_amount = sales_amount+float(sales_data[i].grand_total)
			if sales_amount > 550000:
				return True
	else:
		logging.error("Retailer ID does not exist in Sales Table")
	return False

def execute_rule3(edate):

	# parsing the date field
	parts = edate.split('-')
	days = int(parts[2])
	month = int(parts[1])
	year = int(parts[0])

	if year < 2016 or (month < 2 and year == 2016):
		return True
	else:
		total_days = days
		current_date = time.strftime("%d-%m-%y")
		current_days = int(current_date.split('-')[0])
		current_month = int(current_date.split('-')[1])
		current_year = int(current_date.split('-')[2])
		if current_year > year:
			return True
		else:
			if current_month > month:
				diff = current_month - month
				approx_days = diff*30
		total_days = total_days + approx_days
		if total_days > 180:
			return True
	return False

def rule_based_filtering(cust_id):
	dmap = []
	try:
		check_id = session.query(exists().where(CustomerDetails.Customer_id==cust_id)).scalar()
		if check_id:
			enroll_date = session.query(CustomerDetails.partner_enrollment_date).\
				filter(CustomerDetails.Customer_id==cust_id).first()
			retailer_code = session.query(AlliancePartner.unique_id).\
				filter(AlliancePartner.Customer_id==cust_id).first()
			session.commit()

			if enroll_date and retailer_code:
				enroll_date = enroll_date[0].strftime('%Y-%m-%d')
				rcode = retailer_code[0]

				dmap = prepare_json_obj(rules)
				fobj = dmap

				if execute_rule1(rcode, enroll_date) == True:
					fobj[0]["result"] = "passed"
					sobj = fobj[0]["children"]

					fobj[0]["children"] = []
					if execute_rule2(rcode, enroll_date) == True:
						sobj[0]["result"] = "passed"
						tobj = sobj[0]["children"]

						sobj[0]["children"] = []
						
						if execute_rule3(enroll_date) == True:
							tobj[0]["result"] = "passed"
							lobj = tobj[0]["children"]

							tobj[0]["children"] = []
							if tobj[0]["result"] == "passed":
								lobj[0]["result"] = "passed"
							else:
								lobj[1]["result"] = "failed"
							tobj[0]["children"] = lobj
						else:
							tobj[1]["result"] = "failed"
						sobj[0]["children"] = tobj
					else:
						sobj[1]["result"] = "failed"
					fobj[0]["children"] = sobj
				else:
					fobj[0]["result"] = "failed"
					fail_obj = fobj[0]["children"]
					fobj[0]["children"] = []
					fail_obj[1]["result"] = "failed"

					fobj[0]["children"] = fail_obj
				dmap = fobj
				data = {
				'status_code' : SUCCESS_RULE_FILTER,
				'response_code' :  200,
				'message' : "Success in applying the rule filter",
				'tree_map': dmap
				}
			else:
				data = {
					'status_code': 500,
					'response_code':500,
					'message':"Retailer Code/Enrollment Date not found"
				}
			logging.debug("Successfully created the decision map for the customer")	
			return data
	except Exception, e:
		session.rollback()
		data = {
			'status_code':DATABASE_ERROR,
			'response_code':500,
			'message':"Database Retrieval error",
			'tree_map': dmap
		}
		logging.error("Failure in prepare_customer_scorecard : Database Retrieval error"+" : "+str(e))
		return data
	data = {
		'status_code' : FAILURE_RULE_FILTER,
		'response_code' :  500,
		'message' : "Customer ID does not exist",
		'tree_map':dmap,
	}
	logging.debug("Failure in creating Decision Tree: Customer does not exist")
	return data

def prepare_rule_scorecard(cust_id):
	message = ""
	if len(cust_id) is not 10:
		message = "Invalid ID entered. Please check credentials."
		logging.error(message)
		response_code = 500
		status_code = INVALID_CUSTOMER_ID
		tree_map = None
	else:
		message = rule_based_filtering(cust_id)
	return message

def fetch_customer_id(key, val):
	response_code = 500
	la_id = ''
	check_id = False

	try:
		if key == "mobileNO":
			check_id = session.query(exists().where(CustomerDetails.mobile_no == val)).scalar()
			session.commit()
		elif key == "retailer_id":
			check_id = session.query(exists().where(AlliancePartner.unique_id == val)).scalar()
			session.commit()
		if check_id == True:
			if key == "mobileNO":
				lid = session.query(CustomerDetails.Customer_id).filter(CustomerDetails.mobile_no == val).first()
			elif key == "retailer_id":
				lid = session.query(AlliancePartner.Customer_id).filter(AlliancePartner.unique_id== val).first()
			session.commit()
			
			message = 'Success in retrieving the customer ID for the details provided'
			response_code = 200
			status_code = SUCCESS_CUSTOMER_ID
			la_id = lid[0]
			logging.debug("Success for fetch_customer_id module : Customer_id = "+la_id)
			
		else:
			message = "Customer with " +key +" "+str(val)+" not found in the database. Please check the information provided"
			logging.error(message)
			la_id = 'NA'
			response_code = 500
			status_code = BASIC_DETAIL_ERROR
	except Exception, e:
		session.rollback()
		message = "Database Retrieval error"
		logging.error("Failure in fetch_customer_id module: "+message+" : "+str(e))
		la_id='NA'
		response_code=DATABASE_RETRIEVAL_ERROR
	payload = {}
	payload["msg"] = message
	payload["status"]=response_code
	payload["customer_id"] = la_id

	return response_code,payload

def map_customer_client(customer_id):
	client_id = 'NA'
	if customer_id == 'NA':
		message = "Customer with the ID " +str(customer_id) +" doesn't exist. Please check the information and try again"
		response_code = 500
		status_code = CUSTOMER_ID_ERROR
	else:
		try:
			cid = session.query(CustomerLoanMap.client_id).\
				filter(CustomerLoanMap.Customer_id == customer_id).first()
			if client_id:
				client_id = cid[0]
				session.commit()
				response_code = 200
				status_code = SUCCESS_CLIENT_ID
				message = 'Success on Retrieving Client ID'
				logging.debug("Success for map_customer_to_client module. Client ID: "+str(client_id))
			else:
				client_id = 'NA'
				response_code = 500
				status_code = CLIENT_ID_ERROR
				message = 'Failed to Retrieving a valid/existing client ID'
		except Exception, e:
			session.rollback()
			client_id = 'NA'
			response_code = 500
			status_code = DATABASE_ERROR
			message = "Database Retrieval error"
			logging.error(message+" : "+str(e))
	return message,response_code,status_code,client_id

def fetch_client_info(key, val):
	message = ''
	status_code = 500
	client_id = 'NA'
	[_,result] = fetch_customer_id(key, val)

	# map the key received in the request object to the customer_id
	logging.debug("Customer ID fetched for Client fetching : "+result["customer_id"])
	[message, response_code, status_code, client_id] = map_customer_client(result["customer_id"])
	
	data = {}
	data["msg"] = message
	data["status"] = status_code
	data["client_id"] = client_id
	return response_code,data

# Method to generate OTP
def generate_otp(mobile_no):
	route = "7"

	# generate a random 6-digit number
	otp = random.randint(100000, 999999)
	text = sms_text + str(otp)

	# generating the URL to be requested with appropriate parameters
	SMS_URL = "http://login.smsgatewayhub.com/api/mt/SendSMS?APIKey=" + SMS_GATEWAY_API_KEY + \
		"&senderid=" + sender_id + "&channel=" + channel + "&DCS=" + DCS + "&flashsms=" + flash_sms + \
		"&number=" + str(mobile_no) + "&text=" + text + "&route=" + route


	# Requesting the SMS Gateway Hub URL for sending the OTP
	resp = requests.get(SMS_URL)
	r = json.loads(resp.text)
	logging.debug("SMSGateway Payload : "+str(r))

	# wait for the delivery report to be created
	# time.sleep(5)
	# DELIVERY_URL = "http://www.smsgatewayhub.com/api/mt/GetDelivery?APIKey="+SMS_GATEWAY_API_KEY +\
	# 	"&jobid=" + r["JobId"]
	# delivery_resp = requests.get(DELIVERY_URL)
	# del_r = json.loads(delivery_resp.text)
	# report = del_r["DeliveryReports"][0]
	# logging.debug("Delivery Report : "+report)

	if r["ErrorCode"] == "000":
		status_code = 200
		data = {"message": "OTP sent successfully!", "status": status_code, "content_type": "application/json"}
		data_json = json.dumps(data)
		resp = Response(data_json, 200)
		return resp
	
	logging.error("OTP_Error: OTP sending failed")
	status_code = 500
	data = {"message": "OTP not sent! Please check mobile number", \
		"status": status_code, "content_type": "application/json"}
	data_json = json.dumps(data)
	resp = Response(data_json, 500)
	return resp

def update_age(customer_id):
	try:
		cust_check = session.query(exists().where(CustomerDetails.Customer_id==customer_id)).scalar()
		session.commit()
		if cust_check:
			dob = session.query(CustomerDetails.date_of_birth).filter(CustomerDetails.Customer_id==customer_id).first()
			session.commit()
			dob = dob[0]
			if dob != None:
				today = date.today()
				age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
				session.query(CustomerDetails).with_lockmode('update').\
					filter(CustomerDetails.Customer_id==customer_id).\
					update({"age":age})
				session.commit()
			else:
				age = ""
			return age
		else:
			logging.error("Unable to update age: Customer does not exist")
			return None
	except Exception, e:
		if 'mysql' in str(e).lower():
			session.rollback()
		logging.error("An error occurred : "+str(e))
	return None



		