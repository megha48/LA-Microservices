from lymph.web.interfaces import WebServiceInterface
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Response
from itertools import permutations
from field_op_db import *
import requests
import json
import time
import datetime
import modules
import logging

class FieldOpWeb(WebServiceInterface):

	url_map = Map([
		Rule('/fetch_retailers_list',endpoint = 'fetch_retailers_list'),
		Rule('/store_customer_details', endpoint='store_customer_details'),
		Rule('/get_client_id', endpoint='get_client_id'),
		Rule('/store_kyc_details',endpoint='store_kyc_details'),
		Rule('/fetch_customer',endpoint='fetch_customer'),
		Rule('/filter_applicants', endpoint='filter_applicants')
	])

	def fetch_retailers_list(self,request):

		f_id = request.args["fieldop_id"]

		# fetch retailer list and corresponding state list to display the retailers in different states
		r_list = []
		status_list = []
		resp_data = {}
		[r_list, status_list] = modules.fetch_retailers(f_id)
		resp_data["retailers"] = r_list
		resp_data["status"] = status_list
		resp_json = json.dumps(resp_data)
		resp = Response(resp_json, 200)
		
		h = resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept, Novobank-TenantId, Authorization"
		h['Access-Control-Allow-Methods']= "GET"
		
		return resp

	# getting the client ID of the customer through his phone number
	def get_client_id(self, request):
		id_flag = False
		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)
		if "customer_id" in request.args:
			key = request.args["customer_id"]
			id_flag = True
		elif "mobile_no" in request.args:
			key = request.args["mobile_no"]
		
		print key

		# parse JSON payload to extract phone numbers
		client_id = 0
		message = ""
		response_code = 400
		try:
			if id_flag == False:
				check_mobile = session.query(exists().where(RetailerDetails.retailer_phone == key))
				if check_mobile:
					client_id = session.query(CustomerTable.bank_client_id).filter(CustomerTable.mobile_num == key).first()
					message = "The client ID assigned by the bank for the user is: "+str(client_id[0])
					response_code = 200
				else:	
					message = "The phone number does not exist in our data store. Please try again"
					response_code = 400
			else:
				check_id = session.query(exists().where(RetailerDetails.retailer_id == key))
				if check_mobile:
					client_id = session.query(CustomerTable.bank_client_id).filter(CustomerTable.customer_id == key).first()
					message = "The client ID assigned by the bank for the user is: "+str(client_id[0])
					response_code = 200
				else:	
					message = "The ID provided does not exist in our data store. Please try again"
					response_code = 400
			data = {}
			data["msg"] = message
			resp_data = json.dumps(data)
			resp = Response(resp_data, response_code)
		except Exception,e:
			session.rollback()
			logging.error("MySQLDB error: "+str(e))
			message = "MySQLDB error: "+str(e)
			data = {}
			data["msg"] = message
			resp_data = json.dumps(data)
			resp = Response(resp_data, 400)
		return resp

	# storing the details of the form filled by the Novopay Retailers
	def store_customer_details(self, request):
		
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
		print "Everything OK upto here!"
		return modules.store_customer_details(request)

	# checking if the retailer phone number exists and fetching the retailer phone number
	def fetch_customer(self, request):
		message = ""
		code = 400
		if request.method != 'POST':
			logging.error("POST request error")
			data = {
				"message":"This is meant to be a POST request.",
				"status_code":401
			}

			resp_data = json.dumps(data)
			res = Response(resp_data, 400)
			return res
		
		input_data = json.load(request.stream)
		retailer_phone = input_data["mobile_num"]

		logging.info("about to check if the customer exists in the Data store")
		search_query = session.query(CustomerDetails.mobile_no).filter(customer_type="np_retailer").all()

		# populating the phone_list of retailers
		phone_list = []
		for p in search_query:
			phone_list.append(p[0])

		print phone_list
		if retailer_phone in phone_list:
			logging.info("customer verified")
			retailer_data = session.execute(CustomerDetails.first_name, CustomerDetails.last_name).\
				filter(CustomerDetails.mobile_no == retailer_phone).first()
			name = retailer_data[0] + " "+ retailer_data[1]
			message = "Fetched the details successfully"
			code = 200
		else:
			logging.error("Retailer with the given phone number does not exist")
			message = "Incorrect/Invalid details provided"
			code = 400
		data = {}
		data["message"] = message
		resp_data = json.dumps(data)
		resp = Response(data, code)
		return resp

	# storing the kyc data to the central server
	def store_kyc_details(self, request):
		if request.method != "POST":       
			logging.error("store KYC details: This is a POST request. You made some other Request")
			status_code= POST_REQUEST_ERROR
			data= {"message":"This is a POST request. You made other Request", "status":401, "content_type": 'application/json'}
			data_json= json.dumps(data)
			resp= Response(data_json, 400)
			h= resp.headers
			h['Access-Control-Allow-Origin'] = "*"
			h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
			h['Access-Control-Allow-Methods']= "GET, POST, PUT"
			return resp
		return modules.store_kyc(request)


	def filter_applicants(self,request):
		
		loansapp_id = request.args["loansapp_id"]
		rule_decision = modules.filter_customers(loansapp_id)

		data = {}
		data["msg"] = rule_decision
		resp_json = json.dumps(data)
		resp = Response(resp_json, 200)
		return resp

