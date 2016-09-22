from lymph.web.interfaces import WebServiceInterface
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Response
from itertools import permutations
from los_db import *
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
		Rule('/store_kyc_details',endpoint='store_kyc_details'),
		Rule('/filter_applicant', endpoint='filter_applicant'),
		Rule('/fetch_customer_id', endpoint='fetch_customer_id'),
		Rule('/fetch_loan_info', endpoint='fetch_loan_info'),
		# Rule('/update_doc_status',endpoint='update_doc_status'),
		Rule('/fetch_client', endpoint='fetch_client')
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

	def fetch_customer_id(self,request):
		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)
		
		if "alternate_mobile" in data:
			key = "alternate_mobile"
			val = data["alternate_mobile"]
		elif "retailer_code" in data:
			key = "retailer_code"
			val = data["retailer_code"]

		result = modules.fetch_customer_id(key,val)
		resp_data = json.dumps(result)
		resp = Response(resp_data,int(result["response"]))
		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
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


	def filter_applicant(self,request):

		loansapp_id = request.args["loansapp_id"]
		rule_decision = modules.filter_customers(loansapp_id)

		data = {}
		data["msg"] = rule_decision
		resp_json = json.dumps(data)
		resp = Response(resp_json, 200)
		
		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
		return resp

	def fetch_loan_info(self, request):
		response = 400
		status_code = 200
		# simple GET request
		loansapp_id = request.args["customer_id"]
		amount = 0.0
		tenure_months = 0 
		interest_rate = 0.0
		try:
			data = session.query(CustomerLoanInfo).filter(CustomerLoanInfo.Customer_id == loansapp_id).first()
			print data
			amount = data.loan_amount_req
			tenure_months = data.loan_tenure_desired
			interest_rate = data.loanproduct_interest_rate
			response = 200
			status_code = 201
		except Exception, e:
			logging.error("MySQLDB error:"+str(e))
			response = 500
			status_code = 511
		data = {}
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
		if request.method == 'GET':
			data = request.args
		elif request.method == 'POST':
			req=json.load(request.stream)
			req_json=json.dumps(req)
			data=json.loads(req_json)
		key = ''
		val = ''
		if "alternate_mobile" in data:
			key = "alternate_mobile"
			val = data["alternate_mobile"]
		elif "retailer_code" in data:
			key = "retailer_code"
			val = data["retailer_code"]

		result = modules.fetch_client_info(key,val)
		resp_data = json.dumps(result)
		resp = Response(resp_data,int(result["response"]))
		h= resp.headers
		h['Access-Control-Allow-Origin'] = "*"
		h['Access-Control-Allow-Headers']= "Origin, X-Requested-With, Content-Type, Accept"
		h['Access-Control-Allow-Methods']= "GET, POST, PUT"
		return resp


