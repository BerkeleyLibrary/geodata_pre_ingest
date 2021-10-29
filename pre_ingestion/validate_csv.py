#!/usr/bin/python
import os
import sys
import csv
import json
import datetime
from geo_helper import GeoHelper
import par
import re
if os.name == "nt":
    from jsonschema import validate
    import jsonschema


class ValidateCSV(object):
    def __init__(self,process_path):
        self.csv_files = GeoHelper.dest_csv_files_updated(process_path)
        self.process_path = process_path
        self.arkids = []
        self.main_ark_line = {}

        self.resp_publisher_arkids = []
        self.resp_originator_arkids = []

        self.prepare_main_csv_validation()
        self.prepare_resp_csv_validation()


    def prepare_main_csv_validation(self):
        ark_line_dic = {}
        arkids = []
        with open(self.csv_files[0], 'r') as csvfile:
            print self.csv_files[0]
            csv_reader = csv.DictReader(csvfile)
            line_num = 1
            for main_csv_raw in csv_reader:
                arkid = main_csv_raw["arkid"].strip()
                line_num += 1
                if len(arkid) == 0:
                    GeoHelper.arcgis_message(" warning: line {1}:  in '{0}' has no arkid".format(self.csv_files[0]),str(line_num))
                else:
                    arkids.append(arkid)
                    ark_line_dic[arkid] = str(line_num)
        self.main_ark_line = ark_line_dic
        self.arkids = arkids

    def prepare_resp_csv_validation(self):
        arkids_publisher = []
        arkids_originator = []
        responsible_part_csvfile = self.csv_files[1]
        with open(responsible_part_csvfile, 'r') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            line_num = 0
            for raw in csv_reader:
                arkid = raw["arkid"].strip()

                if len(arkid) == 0:
                    GeoHelper.arcgis_message(" warning: line {1}:  in '{0}' has no arkid".format(self.csv_files[1]),str(line_num))
                else:
                    role = raw["role"].strip().zfill(3)
                    if role == "010":
                        arkids_publisher.append(arkid)
                    if role == "006":
                        arkids_originator.append(arkid)
        self.resp_publisher_arkids = arkids_publisher
        self.resp_originator_arkids = arkids_originator



    def check_default_codes(self,raw,code_list,header):
        messages = []
        column_val = raw[header].strip()
        arkid = raw["arkid"].strip()
        if len(column_val) > 0:
            vals = [txt.strip() for txt in column_val.split("$")]
            for val in vals:
                if not int(val) in code_list:
                    warning_msg = "Warning: line {0}: - '{1}' has incorrect code value -- '{2}' ".format(self.main_ark_line[arkid],header,val)
                    messages.append(warning_msg)
        return messages


    def validate_main_csv_raw(self,raw):
        messages = []

        def add_warning(raw,msg):
            arkid = raw["arkid"].strip()
            warning_msg = "Warning: line {0}:  {1} - {2}".format(self.main_ark_line[arkid],arkid,msg)
            messages.append(warning_msg)

        def check_modified_date_field(raw):
            dt = raw['modified_date_dt'].strip()
            if not GeoHelper.valid_date(dt,'%Y%m%d'):
                msg = "'{0}' needs format in YYYYMMDD".format('modified_date_dt')
                add_warning(raw,msg)

        def check_boolean_fields(raw):
            headers = raw.keys()
            for header in headers:
                if GeoHelper.bool_header(header):
                    val = raw[header].lower()
                    if not val in ["true","false"]:
                        msg = "'{0}': needs a Boolean value ".format(header)
                        add_warning(raw,msg)

        # main csv - 1. make sure columns with header in par.CSV_REQUIRED_HEADERS have values, mandatory metadata elementes
        def check_required_elements(raw):
            required_headers = par.CSV_REQUIRED_HEADERS
            for header in required_headers:
                val = GeoHelper.metadata_from_csv(header,raw)
                if not GeoHelper.isNotNullorEmpty(val):
                    msg = "'{0}': missing required value ".format(header)
                    add_warning(raw,msg)

        # main csv - 2. To avoid typo in accessright element
        def check_accessright(raw):
            rights = ["public","restricted"]
            right = raw["accessRights_s"].strip().lower()
            if len(right) > 0 and (not right in rights):
                msg = "'{0}' value not correct.".format("accessRights_s")
                add_warning(raw,msg)

        # main csv - 3. Make sure input correct topicis code
        def check_topiciso(raw):
            codes = range(1,20)
            warning_msgs = self.check_default_codes(raw,codes,"topicISO")
            warning_msgs_o = self.check_default_codes(raw,codes,"topicISO_o")
            messages.extend(warning_msgs)
            messages.extend(warning_msgs_o)

        # main csv - 4. Make sure Geofile work directory is the same as in main csv file. A user may move the updated CSV files around
        def check_geofile(raw):
            geofile = raw["filename"].strip()
            geopath = GeoHelper.geo_path_from_CSV_geofile(geofile)
            workpath = GeoHelper.work_path(self.process_path)

            correct_geofile = False
            if geopath == workpath:
                if os.path.isfile(geofile):
                    correct_geofile = True
                else:
                    msg = "Missing Geofile: {0}".format(geofile)
                    add_warning(raw,msg)
            else:
                msg = "Work Directory is different! From CSV file - {0}; Actual work directory - {1}".format(geopath,workpath)
                add_warning(raw,msg)
            return correct_geofile

        # def check_sourcetype(raw):
        #     warning_msgs = self.check_default_codes(raw,par.resourceType,"resourceType")
        def check_solr_year(raw):
            def match(reg,str):
                return len(re.findall(reg,str)) == 1

            def match_arr(arr,reg):
                for str in arr:
                    if not match(reg,str):
                        return False
                return True

            def valid_full_years(years):
                reg = '^-?[1-9]\d*$'
                if match_arr(years,reg):
                    return True
                else:
                    msg = "'solrYear' has an invalid year."
                    add_warning(raw,msg)
                    return False

            def valid_four_digit_years(years):
                reg = '^\d{4}$'
                if  not match_arr(years,reg):
                    msg = "'solrYear'is a valid year but not a 4 digital year."
                    add_warning(raw,msg)

            def check_all():
                solr_years = raw["solrYear"]
                if solr_years:
                    years = [yr.strip() for yr in solr_years.split("$")]
                    if valid_full_years(years):
                        valid_four_digit_years(years)
                    else:
                        msg = "'solrYear' is not valid."
                        add_warning(raw,msg)
                else:
                    msg = "'solrYear' has no value."
                    add_warning(raw,msg)


        check_geofile(raw)
        check_required_elements(raw)
        check_topiciso(raw)
        check_accessright(raw)
        check_solr_year(raw)
        check_boolean_fields(raw)
        check_modified_date_field(raw)
        # check_sourcetype(raw)
        return messages


    def validate_main_csv_file(self):
        messages = []
        with open(self.csv_files[0],'r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for raw in csv_reader:  # should we check ISOTopic ?
                raw_msgs = self.validate_main_csv_raw(raw)
                if len(raw_msgs) > 0:  messages.extend(raw_msgs)
        return messages


    def validate_resp_raw(self,raw):
        messages = []
        role = raw["role"].strip().zfill(3)
        individual = raw["individual"].strip()
        organization = raw["organization"].strip()

        def add_warning(raw,msg):
            arkid = raw["arkid"].strip()
            warning_msg = "Warning: arkid {0} in Resp CSV: - {2}".format(arkid,msg)
            messages.append(warning_msg)

        # resp_csv - 1. only role 006 can have "individual value"
        def only_role_006_has_individual():
            if len(individual) > 0 and role <> "006":
                msg = "'{0}' should not have individual. Only role 6 could have individual".format(role)
                add_warning(raw,msg)

        def ensure_006_010_have_values():
            if (role == "006") and len(individual) == 0  and len(organization) == 0:
                msg = "Role '006' should have a value in individual or organization."
                add_warning(raw,msg)
            if (role == "010") and len(organization) == 0:
                msg = "Role '010' should have a value in organization."
                add_warning(raw,msg)

        # resp_csv - 4. Make sure input correct role code
        def ensure_correct_role_code():
            codes = range(1,12)
            msg = self.check_default_codes(raw,codes,"role")
            messages.extend(msg)

        ensure_correct_role_code()
        only_role_006_has_individual()
        ensure_006_010_have_values()
        return messages


    def validate_resp_csv_file(self):
        messages = []
        responsible_part_csvfile = self.csv_files[1]
        with open(responsible_part_csvfile, 'r') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for raw in csv_reader:
                resp_msgs = self.validate_resp_raw(raw)
                messages.extend(resp_msgs)
        return messages




    def validate_required_roles_in_resp_csv(self):
        messeges = []
        for arkid in self.arkids: # main csv file: one geofile - one arkid
            if not arkid in self.resp_publisher_arkids:
                msg = "Warning: Responsible party, {0} - missing 'Publisher (010)' role".format(arkid)
                messeges.append(msg)
            if not arkid in self.resp_originator_arkids:
                msg = "Warning: Responsible party, {0} - missing 'Originator (006)' role".format(arkid)
                messeges.append(msg)
        return messeges



    def updated_csv_files_valid(self):
        def output(ls,file):
            if ls > 0: GeoHelper._print_files_txt(ls,par.MISSING_CVS_VALUES.format(file))

        msg_list_main = self.validate_main_csv_file()
        msg_list_resp =  self.validate_resp_csv_file()
        msg_list_resp_missing_roles = self.validate_required_roles_in_resp_csv()
        msg_list_resp.extend(msg_list_resp_missing_roles)
        msg_list = msg_list_main + msg_list_resp

        if len(msg_list) > 0:
            output(msg_list_main,self.csv_files[0])
            output(msg_list_resp,self.csv_files[1])
            return False
        else:
            GeoHelper.arcgis_message(par.PASS_CSV_VALIDATION)
            return True


    def updated_csv_files_existed(self):
        existed = True
        if len(self.csv_files) <> 2:
            base
            GeoHelper.arcgis_message("Missing updated CSV file in directory '{0}'".format(updated_csv_files_path))
            existed = False
        return existed


    #### Not CSV file - other validations ####

    def files_existed(self,dir,name):
        def full_path_file(dir,arkid,name):
            return os.path.join(dir,arkid,name) # "iso19139.xml"

        missing_files = []
        for arkid in self.arkids:
            file = full_path_file(dir,arkid,name)
            if not os.path.isfile(file):
                missing_files.append(file)
                GeoHelper.arcgis_message("*** Directory '{0}' missing file - '{1}'".format(dir,file))

        return len(missing_files) == 0


    # 1. Check ISO19139 files
    def iso19139_files_existed(self):
        dir = GeoHelper.iso19139_path(self.process_path)
        return self.files_existed(dir,"iso19139.xml")


    # 2. Check geoblacklight files
    def geoblacklight_files_existed(self):
        dir = GeoHelper.geoblacklight_path(self.process_path)
        return self.files_existed(dir,"geoblacklight.json")


    def files_existed_to_zip(self,is_source_file):
        def new_file(old_file):
            if os.name == "nt":
                return old_file.replace("\\Work\\","\\Source\\")
            else:
                return old_file.replace("/Work/","/Source/")

        missing_files = []
        with open(self.csv_files[0], 'r') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for main_csv_raw in csv_reader:
                file = main_csv_raw["filename"].strip()
                the_file = new_file(file) if is_source_file else file
                if not os.path.isfile(the_file):
                    missing_files.append(the_file)
                    GeoHelper.arcgis_message("*** Missing file - '{0}'".format(the_file))

        return len(missing_files) == 0


    # 3. check work files ready for map.zp
    def work_files_existed(self):
        return self.files_existed_to_zip(False)


    # 4. check source files ready for download  data.zip
    def source_files_existed(self):
        return self.files_existed_to_zip(True)


    # 5. check download zip files existing for merrritt
    def data_zip_files_existed(self):
        dir = GeoHelper.data_download_path(self.process_path)
        return self.files_existed(dir,"data.zip")


    ### Geoblacklight JSON veridation ###
    def ardvark_validation(self):
        schema_path = os.path.join(os.path.dirname(__file__),"validation")
        ardvark_schema = os.path.join(schema_path,"GeoblacklightTransform.json")

        def validation(file):
            isvalid = False
            schema = ""
            data = ""

            with open(ardvark_schema,'r') as s:
                schema = s.read()
            with open(file,'r') as d:
                data = d.read()

            try:
                v = jsonschema.Draft4Validator(json.loads(schema))
                for error in sorted(v.iter_errors(json.loads(data)), key=str):
                    errorMessage = error.message.replace("u\'","\'")
                    msg = "* " + errorMessage
                    if len(error.path) > 0:
                        msg = "* " + error.path[0] + ': ' + errorMessage
                    GeoHelper.arcgis_message(msg)

            except jsonschema.ValidationError as e:
                msg = "^^ Geoblackschema error when validating {0} : error --  {1}".format(file,e.message)
                GeoHelper.arcgis_message(msg)
            except:
                GeoHelper.arcgis_message("^^ ardvark_validation error -- {0}".format(e.message))

        def validation_all():
            geoblacklight_dir = GeoHelper.geoblacklight_path(self.process_path)
            for root, dirs, files in os.walk(geoblacklight_dir):
                for file in files:
                    json_file = os.path.join(root,file)

                    ext = os.path.splitext(json_file)[1].lower()
                    if ext == ".json":
                        if os.name == "nt":
                            validation(json_file)

        validation_all()
