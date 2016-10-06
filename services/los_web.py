from lymph.web.interfaces import WebServiceInterface
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Response
from itertools import permutations
from los_db import *
from status_codes import *
from pymongo import MongoClient
from bson.objectid import ObjectId
from authorization import authorization
import gridfs
import requests
import json
import time
import datetime
import modules
import mimetypes
import logging
import os
import re
import yaml
import cgi

class LosWeb(WebServiceInterface):

	log_file = os.path.abspath('services/logging.conf')
	logging.config.dictConfig(yaml.load(open(log_file)))
	logging= logging.getLogger('root')
	
	logging.debug("LYMPH started!")

	url_map = Map([
		Rule("/los/v1/fetch_retailers_list",endpoint = 'fetch_retailers_list'),
		Rule("/los/v1/fetch_customer_info",endpoint = 'fetch_customer_info'),
		Rule("/los/v1/fetch_dendogram", endpoint = 'fetch_dendogram'),
		Rule("/los/v1/update_lo_result", endpoint = 'update_credit_officer_result'),
		Rule("/los/v1/store_customer_details", endpoint='store_customer_details'),
		Rule("/los/v1/store_kyc_details",endpoint='store_kyc_details'),
		Rule("/los/v1/prepare_customer_scorecard", endpoint='prepare_customer_scorecard'),
		Rule("/los/v1/fetch_customer_id", endpoint='fetch_customer_id'),
		Rule("/los/v1/fetch_loan_info", endpoint='fetch_loan_info'),
		Rule('/los/v1/update_doc_status',endpoint='update_doc_status'),
		Rule("/los/v1/fetch_client", endpoint='fetch_client'),
		Rule("/los/v1/map_customer_to_client",endpoint='map_customer_to_client'),
		Rule("/los/v1/send_otp", endpoint='send_otp'),
		Rule("/los/v1/download_docs", endpoint='download_docs'),
		Rule("/los/v1/render_document_status", endpoint='render_document_status')
	])

	@staticmethod
	def validate_access(request):
		authObj = authorization()
		token = request.headers.get('Authorization')
		if(token == None):
			log_msg = json.dumps({'statusCode': 401, 'message': "Authorization Header missing"})
			return Response(log_msg, 401)

		authResult = authObj.validateAuthorization(token)
		if (authResult == True):
			return None
		else:
			log_msg = json.dumps({'statusCode': 401, 'message': "Not a valid token"})
			return Response(log_msg, 401)
	
	def fetch_retailers_list(self,request):
		
		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)

		try:
			customer_list = session.query(CustomerDetails).filter(CustomerDetails.first_name != None).all()
			session.commit()
			customer_info = []

			for cust in customer_list:
				customer_obj = {}
				fname = cust.first_name
				lname = cust.last_name
				pan = session.query(CustomerPersonal.PAN_no).filter(CustomerPersonal.Customer_id==cust.Customer_id).first()
				session.commit()
				if pan != None:
					pan_no = pan[0]
				else:
					pan_no = ""
				
				alliance_partner = "Novopay"
				region = ""
				comments = ""
				customer_status = ""
				
				cust_status = session.query(CustomerState).filter(CustomerState.Customer_id==cust.Customer_id).first()
				session.commit()
				if cust_status:
					if cust_status.credit_officer_decision_flag == 1:
						customer_status = "Approved"
						comments = cust_status.credit_officer_comments
					elif cust_status.credit_officer_decision_flag == 0:
						customer_status = "Rejected"
						comments = cust_status.credit_officer_comments
					else:
						customer_status = "Pending"
						# session.query(CustomerState).with_lockmode('update').\
						# 	filter(CustomerState.Customer_id==cust.Customer_id).\
						# 	update({"loan_evaluation_started_flag":1}, synchronize_session='fetch')
				else:
					# los_engine.execute(CustomerState.__table__.insert(),\
					# 	Customer_id=cust.Customer_id,loan_evaluation_started_flag=1)
					customer_status = "Pending"

				customer_obj = {
					"id":cust.Customer_id,
					"firstName":fname,
					"lastName":lname,
					"pan":pan_no,
					"alliancePartner":alliance_partner,
					"region":region,
					"decision":customer_status,
					"comments":comments,
					"loansappScore":0
				}
				customer_info.append(customer_obj)	

			cust_data = {
				"draw":1,
				"data":customer_info,
				"recordsFiltered":12,
				"recordsTotal":12
			}

			data_json = json.dumps(cust_data)
			resp = Response(data_json, 200)
		except Exception, e:
			if 'mysql' in (str(e)).lower():
				session.rollback()
				cust_data = {
					"message":"Database Retrieval Error in fetching retailers list",
					"status_code":DATABSE_RETRIEVAL_ERROR
				}
			else:
				cust_data = {
					"message":"some exception in fetching retailers list",
					"status_code":500
				}
			logging.error(cust_data["message"]+ " : "+str(e))
			data_json = json.dumps(cust_data)
			resp = Response(data_json, 500)

		h = resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept, Novobank-TenantId, Authorization"
		h['Access-Control-Allow-Methods']= "GET"
		
		return resp

	def fetch_customer_info(self,request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)

		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)

		customer_id = data["customer_id"]

		try:
			fname, lname, age, email, mobile_no, paddress, caddress, occupation, nationality, father_name, mother_name = ("" for i in range(11))
			cust_check = session.query(exists().where(CustomerDetails.Customer_id==customer_id)).scalar()
			session.commit()
			if cust_check:
				fname, lname, dob, mobile_no, email = session.query(CustomerDetails.first_name, CustomerDetails.last_name, \
					CustomerDetails.date_of_birth, CustomerDetails.mobile_no, CustomerDetails.email_address).\
					filter(CustomerDetails.Customer_id==customer_id).first()
				session.commit()
				if dob:
					age = modules.update_age(customer_id)
					if age == None:
						age = ""
				cust_personal_check = session.query(exists().where(CustomerPersonal.Customer_id==customer_id)).scalar()
				if cust_personal_check:
					personal_info = session.query(CustomerPersonal).\
						filter(CustomerPersonal.Customer_id==customer_id).first()
					session.commit()
					if personal_info.permanent_address:
					 	paddress = personal_info.permanent_address
					if personal_info.communication_address:
						caddress = personal_info.communication_address
					if personal_info.occupation:
						occupation = personal_info.occupation
					if personal_info.nationality:
						nationality = personal_info.nationality
					if personal_info.father_name:
						father_name = personal_info.father_name
					if personal_info.mother_maiden_name:
						mother_name = personal_info.mother_maiden_name

				name = fname+" "+lname
				res_data = {
					"name":name,
					"age" : age,
					"mobile_no":mobile_no,
					"emailID":email,
					"p_address":paddress,
					"c_address":caddress,
					"occupation":occupation,
					"father_name":father_name,
					"mother_name":mother_name,
					"nationality":nationality,
					"message":"Success on retrieving basic information of customer",
					"status_code":211
				}
				resp_data = json.dumps(res_data)
				resp = Response(resp_data, 200)
				logging.debug("Result received : "+res_data["message"]+" "+str(res_data["status_code"]))
			else:
				logging.error("Unable to fetch details : Customer not found in our records.")
				res_data = {
					"message":"Unable to fetch details : Customer not found in our records.",
					"status_code":501
				}
				resp_data = json.dumps(res_data)
				resp = Response(resp_data, 500)
		except Exception as e:
			if 'mysql' in str(e).lower():
				logging.error("Database Retrieval Error : "+str(e))
				res_data = {
					"message": "Database Retrieval Error : "+str(e),
					"status_code" : DATABSE_RETRIEVAL_ERROR
				}
			else:
				logging.error("Some error : "+str(e))
				res_data = {
					"message": "Some Error : " + str(e),
					"status_code" : DATABSE_RETRIEVAL_ERROR
				}
			resp_data = json.dumps(res_data)
			resp = Response(resp_data, 500)

		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
		return resp

	def fetch_dendogram(self, request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)

		logging.debug("Preparing to fetch the Sankey Diagram for LOS: No paramters required")
		customer_list = session.query(CustomerDetails).filter(CustomerDetails.first_name != None).all()
		scored = 0
		not_scored = 0
		being_scored = 0
		approved = 0
		rejected = 0
		pending = 0
		disbursed = 0

		try:
			for cust in customer_list:
				cust_id = cust.Customer_id
				scored_flag = session.query(DocumentStatus).\
					filter(DocumentStatus.Customer_id==cust_id).filter(DocumentStatus.doc_id=='CIBIL').filter(DocumentStatus.upload_flag==1).count()
				session.commit()
				being_scored_flag = session.query(DocumentStatus).\
					filter(DocumentStatus.Customer_id==cust_id).filter(DocumentStatus.doc_id=='CIBIL').filter(DocumentStatus.upload_flag==None).count()
				session.commit()
				not_scored_flag = session.query(DocumentStatus).\
					filter(DocumentStatus.Customer_id==cust_id).count()
				session.commit()
				if scored_flag:
					scored = scored+1
					approved_flag = session.query(CustomerState).\
						filter(CustomerState.Customer_id==cust_id).\
						filter(CustomerState.credit_officer_decision_flag==1).count()
					session.commit()
					rejected_flag = session.query(CustomerState).\
						filter(CustomerState.Customer_id==cust_id).\
						filter(CustomerState.credit_officer_decision_flag==0).count()
					session.commit()
					pending_flag = session.query(CustomerState).\
						filter(CustomerState.Customer_id==cust_id).\
						filter(CustomerState.credit_officer_decision_flag==None).count()
					session.commit()
					if approved_flag:
						approved=approved+1
						disbursed_flag = session.query(CustomerState).\
							filter(CustomerState.Customer_id==cust_id).\
							filter(CustomerState.loan_disbursed_flag==1).count()
						session.commit()
						if disbursed_flag:
							disbursed = disbursed + 1
					if rejected_flag:
						rejected = rejected + 1
					if pending_flag:
						pending = pending + 1


				if not not_scored_flag:
					not_scored = not_scored + 1
				if being_scored_flag:
					being_scored = being_scored + 1

			sankey = modules.prepare_dendogram_struct()

			edges = sankey["links"]

			for e in edges:
				if e["source"] == "Scored":
					if e["target"] == "Awaiting":
						e["value"] = pending
					elif e["target"] == "Approved":
						e["value"] = approved
					elif e["target"] == "Rejected":
						e["value"] = rejected
				if e["source"] == "Approved":
					if e["target"]=="Disbursed":
						e["value"] = disbursed

			extras = sankey["extra_nodes"]
			for ex in extras:
				if ex["node_name"]=="Not Scored":
					ex["value"] = not_scored
				elif ex["node_name"] == "Currently Scoring":
					ex["value"] = being_scored

			sankey["links"] = edges
			sankey["extra_nodes"] = extras
			data = {
				"result": sankey,
				"status_code":207,
				"message":"Successfully populated the dendogram"
			}
			logging.debug(data["message"])
			
			data_json = json.dumps(data)
			resp = Response(data_json,200)
			
		except Exception, e:
			session.rollback()
			logging.error("Database retrieval error : "+str(e))
			data={
				"result":{},
				"status_code":DATABSE_RETRIEVAL_ERROR,
				"message":"Database retrieval error"
			}
			data_json = json.dumps(data)
			resp = Response(data_json,500)

		
		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
		return resp

	def update_credit_officer_result(self, request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)

		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)

		cust_id = data["customer_id"]
		approve_state = data["result"]
		comment = data["comments"]
		change = ""

		appr = int(approve_state)
		if appr == 1:
			change = "approved"
		else:
			change = "rejected"

		try:
			cust_check = session.query(exists().where(CustomerState.Customer_id==cust_id)).scalar()
			session.commit()

			if cust_check:
				session.query(CustomerState).with_lockmode('update').\
					filter(CustomerState.Customer_id==cust_id).\
					update({"credit_officer_decision_flag":appr, "credit_officer_comments":comment},synchronize_session='fetch')
				session.commit()
			else:
				los_engine.execute(CustomerState.__table__.insert(),\
					Customer_id=cust_id, credit_officer_decision_flag=appr, credit_officer_comments=comment)
				session.commit()
			
			audit_check = session.query(AuditTable).all()
			session.commit()
			source_ip = request.headers.get("X-Real-IP")
			if source_ip == None:
				source_ip = "127.0.0.1"
			audit_json = {
				"c_id":cust_id,
				"l_id":"",
				"state_change":change,
				"ip":source_ip
			}
			audit_obj = json.dumps(audit_json)
			if audit_check:
				random_id = audit_check[-1].id + 1
				los_engine.execute(AuditTable.__table__.insert(),\
					id=random_id, audit_log=audit_obj)
				session.commit()
			else:
				los_engine.execute(AuditTable.__table__.insert(),\
					id=1, audit_log=audit_obj)
				session.commit()
			data = {
				"message":"Success",
				"status_code":207
			}
			resp_data = json.dumps(data)
			resp = Response(resp_data, 200)
		except Exception, e:
			logging.error("Error in update_credit_officer_result : "+str(e))
			data = {
				"message":"Error",
				"status_code":502
			}
			resp_data = json.dumps(data)
			resp = Response(resp_data, 500)
		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
		return resp

	def fetch_customer_id(self,request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)

		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)
		
		logging.debug("Fetching the customer ID for LoansApp with request parameters: "+str(data))

		if "mobileNO" in data:
			key = "mobileNO"
			val = data["mobileNO"]
		elif "retailer_id" in data:
			key = "retailer_id"
			val = data["retailer_id"]

		response, result = modules.fetch_customer_id(key,val)
		resp_data = json.dumps(result)

		logging.debug("Response for fetching the customer ID for Loansapp: "+ str(resp_data))

		resp = Response(resp_data,int(response))
		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
		return resp

	# storing the details of the form filled by the Novopay Retailers
	def store_customer_details(self, request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)
		
		if request.method != 'POST':
			logging.error("This is meant to be a POST request. You seemed to have made an invalid request.")
			status_code= 401
			data= {"message":"This is a POST request. You made other Request", "status":status_code, "content_type": 'application/json'}
			data_json= json.dumps(data)
			resp= Response(data_json, 400)
			h= resp.headers
			h['Access-Control-Allow-Origin'] = "*"
			h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
			h['Access-Control-Allow-Methods']= "GET, POST, PUT"
			return resp
		return modules.store_customer_details(request)

	# storing the kyc data to the central server
	def store_kyc_details(self, request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)
		
		if request.method != "POST":       
			logging.error("store KYC details: This is a POST request. You made some other Request")
			status_code= POST_REQUEST_ERROR
			data= {"message":"This is a POST request. You made other Request", "status":status_code, "content_type": 'application/json'}
			data_json= json.dumps(data)
			resp= Response(data_json, 400)
			h= resp.headers
			h['Access-Control-Allow-Origin'] = "*"
			h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
			h['Access-Control-Allow-Methods']= "GET, POST, PUT"
			return resp
		return modules.store_kyc(request)

	# service to filter a specific retailer on the basis of rules framed by Novopay
	def prepare_customer_scorecard(self,request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)

		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)

		customer_id = data["customer_id"]
		logging.debug("Parameters for filtering customers based on Rule System: Customer ID - "+customer_id)
		rule_decision = modules.prepare_rule_scorecard(customer_id)

		data = {}
		data["decision_tree"] = rule_decision["tree_map"]
		data["status_code"] = rule_decision["status_code"]
		data["message"] = rule_decision["message"]
		resp_json = json.dumps(data)
		resp = Response(resp_json, int(rule_decision["response_code"]))
		
		logging.debug("Response for filtering customers based on Rule System: "+str(resp))

		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
		return resp

	def fetch_loan_info(self, request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)
		
		response = 500
		status_code = 200
		# simple GET request
		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)

		loansapp_id = data["customer_id"]

		logging.debug("Parameters for retrieving the loan information of the customer: "+str(loansapp_id))

		amount = 0.0
		tenure_months = 0 
		interest_rate = 0.0
		try:
			data = session.query(CustomerLoanInfo).filter(CustomerLoanInfo.Customer_id == loansapp_id).first()
			session.commit()
			if data:
				message="Success in getting loan details of customer"
				amount = data.loan_amount_req
				tenure_months = data.loan_tenure_desired
				interest_rate = data.loanproduct_interest_rate
				response = 200
				status_code = SUCCESS_LOAN_INFO
			else:
				message = "Customer has not applied for a loan yet."
				response = 200
				status_code = LOAN_INFO_ERROR
		except Exception, e:
			logging.error("Error:"+str(e))
			response = 500
			status_code = DATABASE_ERROR
		data = {}
		data["message"] = message
		data["loan_amount"] = float(amount)
		data["loan_tenure"] = int(tenure_months)
		data["loan_interest_rate"] = float(interest_rate)
		data["status_code"] = status_code
		resp_data = json.dumps(data)
		resp = Response(resp_data, response)
		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
		return resp

	def fetch_client(self, request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)

		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)
		key = ''
		val = ''
		if "mobileNO" in data:
			key = "mobileNO"
			val = data["mobileNO"]
		elif "retailer_id" in data:
			key = "retailer_id"
			val = data["retailer_id"]

		response_code,result = modules.fetch_client_info(key,val)

		resp_data = json.dumps(result)
		resp = Response(resp_data,int(response_code))
		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
		return resp

	def map_customer_to_client(self, request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)

		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)
		customer_id = data["customer_id"]

		message,response,status_code,client_id = modules.map_customer_client(customer_id)

		data = {
			"msg" : message,
			"status":status_code,
			"client_id":client_id,
		}
		resp_data = json.dumps(data)
		resp = Response(resp_data,response)
		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
		return resp

	# generate OTP and send it to the entered mobile number
	def send_otp(self, request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)

		mobile_no=""

		# pattern = re.compile("/^(\+\d{1,3}[- ]?)?\d{10}$/")
		
		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)
		
		mobile_no = data["mobileNO"]
		
		if mobile_no.isdigit() and len(mobile_no)==10:
			logging.debug("Sending OTP to the given number...")
			resp = modules.generate_otp(mobile_no)
			return resp
		
		logging.error("Error encountered while sending OTP to registered mobile number: Invalid mobile number entered")
		status_code = INVALID_MOBILE_NUMBER
		data = {"message": "Invalid Mobile Number", "status": status_code, "content_type": "application/json"}
		data_json = json.dumps(data)
		resp = Response(data_json, 500)
		return resp

	# fetch status of upload of different documents on the portal
	def render_document_status(self, request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)

		response = 500
		status_code = 200
		status_map = {}
		doc_ids = []
		doc_status_list = []
		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)

		customer_id = data["customer_id"]
		logging.debug("Parameters for rendering documents on the LoansApp Portal: "+str(request.args))
	
		try:
			cust_exists = session.query(exists().where(CustomerDetails.Customer_id == customer_id)).scalar()
			session.commit()
			logging.debug("Checking for customer existence : "+str(cust_exists))
			if cust_exists:
				cust_doc_exists = session.query(exists().where(CustomerKYC.Customer_id==customer_id)).scalar()
				cust_kyc_exists = session.query(exists().where(DocumentStatus.Customer_id==customer_id)).scalar()
				session.commit()

				logging.debug("Checking for customer has given any documents : "+str(cust_doc_exists)+" "+str(cust_kyc_exists))
				if cust_kyc_exists or cust_doc_exists:

					doc_list = session.query(DocumentStatus.doc_id,DocumentStatus.upload_flag).\
						filter(DocumentStatus.Customer_id==customer_id).all()
					session.commit()
					logging.debug("Checking for documents: "+str(doc_list))
					
					if doc_list:
						for i in range(len(doc_list)):
							if doc_list[i][1]:
								doc_ids.append(doc_list[i][0])
								doc_status_list.append(doc_list[i][1])

					kyc_list = session.query(CustomerKYC.id_proof_type, CustomerKYC.address_proof_type,\
						CustomerKYC.id_proof_flag, CustomerKYC.address_proof_flag).\
						filter(CustomerKYC.Customer_id == customer_id).first()
					session.commit()

					# checking if KYC documents have been uploaded to the server
					if kyc_list:
						if kyc_list[2]:
							doc_ids.append(kyc_list[0])
							doc_status_list.append(kyc_list[2])	
						if kyc_list[3]:
							doc_ids.append(kyc_list[1])
							doc_status_list.append(kyc_list[3])

					for i in range(len(doc_ids)):
						status_map[doc_ids[i]] = doc_status_list[i]
					response = 200
					status_code = DOC_RENDER_SUCCESS
					logging.debug("Response for rendering documents on the LoansApp Portal"+str(status_map))
					message = "Success in retrieving the status of the documents uploaded for customer: "+str(customer_id) 
				else:
					message = "Customer "+customer_id+" has not submitted any documents yet!"
					status_code = DOC_RENDER_ERROR
					response = 200
			else:
				message = "Customer "+customer_id+" does not exist in our records"
				status_code = CUSTOMER_ID_ERROR
		except Exception, e:
			session.rollback()
			response = 500
			status_code = DATABASE_ERROR
			message = "Database Retrieval Error"
			logging.error("Database Retrieval Error: "+str(e))
		data = {
			"message":message,
			"doc_map":status_map,
			"status_code":status_code
		}
		data_json = json.dumps(data)
		resp = Response(data_json, response)
		return resp

	# downloading documents from MongoDB
	def download_docs(self, request):

		# validate access through gateway
		result = LosWeb.validate_access(request)
		if(result != None):
			return(result)


		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)

		# getting databases name and pointer to Grid File System
		try:
			mport = int(MONGO_PORT)
			db = MongoClient(MONGO_HOSTNAME, mport).test
			fs = gridfs.GridFS( db )
		except Exception, e:
			status_code= 500
			data= {"message":"Error ocurred while setting up connection with MongoDB"}
			logging.error("Error ocurred while setting up connection with MongoDB: "+str(e))
			data_json= json.dumps(data)
			resp= Response(response= data_json, status=status_code, content_type= 'application/json')
			h= resp.headers
			h['Access-Control-Allow-Origin'] = "*"
			h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
			h['Access-Control-Allow-Methods']= "GET, POST, PUT"
			return resp
		# getting the corresponding file handle and preparing the document for download
		try:
			fid = ''
			doc_id = data["doc_id"]
			cust_id = data["customer_id"]
			
			logging.debug("Parameters passed for download_docs microservice: "+str(request.args))

			if doc_id.startswith('KYC'):
				doc_type = session.query(DocumentDetails.doc_type).filter(DocumentDetails.doc_id==doc_id).first()
				session.commit()

				doc_type = doc_type[0]
				if doc_type == 'Proof of Identity':
					fid = session.query(CustomerKYC.id_proof_fileloc).filter(CustomerKYC.Customer_id==cust_id).first()
					session.commit()
				elif doc_type == 'Proof of Identity/Address':
					fid = session.query(CustomerKYC.address_proof_fileloc).filter(CustomerKYC.Customer_id==cust_id).first()
					session.commit()
			else:
				fid = session.query(DocumentStatus.doc_path).\
					filter(DocumentStatus.Customer_id == cust_id, DocumentStatus.doc_id==doc_id).first()
				session.commit()

			file_id = ObjectId(fid[0])
			if file_id:
				status_code = 200
				file_to_download = fs.get(file_id)
				file_extension = str(file_to_download.name)[(str(file_to_download.name).index('.')):]
				resp = Response( response=file_to_download.read(), status=status_code )
				resp.headers['Content-Type'] = (mimetypes.types_map[file_extension])
				resp.headers['Content-Disposition'] = 'attachment; filename=' + file_to_download.name
				resp.content_length = file_to_download.length
				h= resp.headers
				h['Access-Control-Allow-Origin'] = "*"
				h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
				h['Access-Control-Allow-Methods']= "GET, POST, PUT"
				logging.debug("File - " +file_to_download.filename +" for "+cust_id+" downloaded successfully!")
				return resp
		except Exception, e:
			status_code= 500
			data= {"message":"Error ocurred while downloading file"}
			logging.error("Exception raised while downloading file: "+str(e))
			data_json= json.dumps(data)
			resp= Response(response= data_json, status=status_code, content_type= 'application/json')
			h= resp.headers
			h['Access-Control-Allow-Origin'] = "*"
			h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
			h['Access-Control-Allow-Methods']= "GET, POST, PUT"
			return resp


