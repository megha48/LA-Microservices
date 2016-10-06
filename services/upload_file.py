import gridfs
import os
import StringIO
import base64
import logging
import datetime
import shutil
from os import listdir
from os.path import isfile, isdir, join
from pymongo import MongoClient
from bson.objectid import ObjectId
from los_db import *

# inserting files into MongoDB via MongoClient

mport = int(MONGO_PORT)
client = MongoClient(MONGO_HOSTNAME, mport)
doc_db = client.test
doc_fs = gridfs.GridFS(doc_db)

filepath = "/Users/megha/Documents/Test_Upload/"

# parsing the directory structure to upload the documents
def parse_directory(filepath):
	file_id=""
	customer_id=""
	root_dir = listdir(filepath)

	print "Here"

	for f in root_dir:
		print f
		if isdir(os.path.join(filepath, f)) and f=='Collected':
			inner_path = os.path.join(filepath,f)
			inner_dir = listdir(inner_path)
			for in_file in inner_dir:
				
				if not in_file.startswith('.'):
					print in_file
					doc_path = os.path.join(inner_path,in_file)
					if isdir(doc_path):
						retailer_folder = listdir(doc_path)
						if retailer_folder:
							for docs in retailer_folder:
								if not docs.startswith('.'):
									doc_name = docs.split('.')[0]

									# doc_name being the retailer_code checked for existence in the database
									try:
										cust_id = session.query(AlliancePartner.Customer_id).filter(AlliancePartner.unique_id==in_file).first()
										customer_id = cust_id[0]
									except Exception, e:
										session.rollback()
										logging.error("Database Retrieval Error: "+str(e))
								
									# reading the file and uploading it to Mongo DB
									r_doc = open(os.path.join(doc_path, docs),"r")
									text = r_doc.read()
									file_id = doc_fs.put(text, filename=docs)
									doc_attr = session.query(DocumentDetails.doc_id, DocumentDetails.doc_type).\
										filter(DocumentDetails.doc_alias==doc_name.lower()).first()

									# storing details in the database
									store_document_status(in_file, file_id, customer_id, doc_attr, docs)
						else:
							print("All files have been processed")

def store_document_status(retailer_id, file_id, customer_id, doc_attr, doc_name):
	doc_id = doc_attr[0]
	doc_type = doc_attr[1]
	print doc_id
	print doc_type
	try:
		if doc_id.startswith('KYC'):
			cust_exists = session.query(exists().where(CustomerKYC.Customer_id == customer_id)).scalar()
			if cust_exists:
				if doc_type == "Proof of Identity/Address":
					session.query(CustomerKYC).\
						filter(CustomerKYC.Customer_id==customer_id).\
						update({"kyc_mode":"offline", "address_proof_flag":1, "id_proof_flag":1,\
							"id_proof_type":doc_id, "address_proof_type":doc_id,\
							 "id_proof_fileloc":file_id, "address_proof_fileloc":file_id})
				elif doc_type == "Proof of Identity":
					session.query(CustomerKYC).\
						filter(CustomerKYC.Customer_id==customer_id).\
						update({"kyc_mode":"offline", "id_proof_flag":1,\
							"id_proof_type":doc_id, "id_proof_fileloc":file_id})
			else:
				if doc_type == "Proof of Identity/Address":
					los_engine.execute(CustomerKYC.__table__.insert(),\
						Customer_id = customer_id,kyc_mode="offline", address_proof_flag=1, id_proof_flag=1,\
						id_proof_type=doc_id, address_proof_type=doc_id,\
						id_proof_fileloc=file_id, address_proof_fileloc=file_id)
				elif doc_type == "Proof of Identity":
					los_engine.execute(CustomerKYC.__table__.insert(),\
						Customer_id=customer_id, kyc_mode="offline", id_proof_flag=1,\
						id_proof_type=doc_id, id_proof_fileloc=file_id)
			session.commit()
		else:
			cust_exists = session.query(exists().\
				where(DocumentStatus.Customer_id==customer_id and DocumentStatus.doc_id==doc_id)).scalar()

			if cust_exists:
				session.query(DocumentStatus).\
					filter(DocumentStatus.Customer_id==customer_id).filter(DocumentStatus.doc_id==doc_id).\
					update({"doc_path":file_id, "upload_flag":1, "upload_timestamp":datetime.datetime.now()})
			else:
				los_engine.execute(DocumentStatus.__table__.insert(),\
					Customer_id=customer_id, doc_id=doc_id, doc_path=file_id, upload_flag=1,\
					upload_timestamp=datetime.datetime.now())
			session.commit()
	except Exception, e:
		session.rollback()
		logging.error("Database Retrieval Error: " +str(e))
	
	# after updating the status of documents, move the files to the Uploaded Folder
	
	folder = (os.path.join(filepath,'Collected/'))
	dest_root = os.path.join(filepath,'Uploaded')
	dest_folder = os.path.join(dest_root, retailer_id)
	if not os.path.exists(dest_folder):
		os.makedirs(dest_folder)
	inner_folder = os.path.join(folder,retailer_id)
	shutil.move(os.path.join(inner_folder, doc_name), dest_folder)

def store_cibil_report(filepath):
	root_dir = listdir(filepath)
	for f in root_dir:
		if isdir(os.path.join(filepath, f)) and f=='Collected':
			inner_path = os.path.join(filepath,f)
			inner_dir = listdir(inner_path)
			for in_file in inner_dir:
				print in_file
				if not in_file.startswith('.'):
					doc_path = os.path.join(inner_path,in_file)
					if isdir(doc_path):
						retailer_folder = listdir(doc_path)
						if retailer_folder:
							for rfile in retailer_folder:
								rfile_name = rfile.split('.')[0]
								if rfile_name.lower() == 'cibil':
									try:
										cust_id = session.query(AlliancePartner.Customer_id).\
											filter(AlliancePartner.unique_id==in_file).first()
										print cust_id
										cust_id = cust_id[0]

										if cust_id:
											r_doc = open(os.path.join(doc_path, rfile),"r")
											text = r_doc.read()
											file_id = doc_fs.put(text, filename=rfile)

											doc_id = session.query(DocumentDetails.doc_id).\
													filter(DocumentDetails.doc_alias==rfile_name.lower()).first()[0]
											print doc_id, cust_id
											cust_check = session.query(exists().\
												where(DocumentStatus.Customer_id=='LA' and DocumentStatus.doc_id=='CIBIL')).scalar()
											print cust_check
											if cust_check:
												session.query(DocumentStatus).with_lockmode('update').\
													filter(DocumentStatus.Customer_id==cust_id).filter(DocumentStatus.doc_id==doc_id).\
													update({"upload_flag":1, "collect_flag":1, "doc_path":file_id}, synchronize_session='fetch')
											else:
												los_engine.execute(DocumentStatus.__table__.insert(),\
													Customer_id=cust_id, doc_id=doc_id, doc_path=file_id, collect_flag=1, upload_flag=1)
											logging.debug("File uploaded successfully to server")
											folder = inner_path
											dest_root = os.path.join(filepath,'Uploaded')
											dest_folder = os.path.join(dest_root, in_file)
											if not os.path.exists(dest_folder):
												os.makedirs(dest_folder)
											inner_folder = os.path.join(folder, in_file)
											shutil.move(os.path.join(inner_folder, rfile), dest_folder)
										else:
											logging.warn("Customer ID does not exist in our records")
									except Exception, e:
										logging.error("Database Retrieval Error : "+str(e))
								


store_cibil_report(filepath)

# parse_directory(filepath)







