#!/usr/bin/python
import os
import xml.etree.ElementTree as ET
import csv
import par
import json
import re
# from datetime import datetime
import datetime
from geo_helper import GeoHelper
if os.name == "nt":
    import arcpy


# Geoblacklight metadata from:
# 1) CSV
# 2) Default values
# 3) Drived from arkid
# 4) Extracted from iso19139
# 5) From obj - gotten from reponsible party csv file
# 6) Todo: add multiple resource download after geoblacklight v4

class CsvGeoblacklight(object):
    def __init__(self,raw_obj,process_path):
        self.raw_obj = raw_obj
        self.main_csv_raw = raw_obj.__dict__["_main_csv_raw"]
        self.main_csv_headers = self.main_csv_raw.keys()

        self.arkid = self.main_csv_raw["arkid"].strip()
        self.geofile = self.main_csv_raw["filename"].strip()
        self.process_path = process_path


    def create_geoblacklight_file(self):
        def geoblacklight_file():
            geoblacklight_dir = GeoHelper.geoblacklight_path(self.process_path)
            path = os.path.join(geoblacklight_dir,self.arkid)
            if not os.path.exists(path):
                os.makedirs(path)
            return os.path.join(path,"geoblacklight.json")

        def save_pretty():
            json_data = {}
            self._add_from_main_csv(json_data)
            self._add_from_responsible_csv(json_data)
            self._add_from_default(json_data)
            self._add_from_arkid(json_data)
            self._add_boundary(json_data)

            with (open(geoblacklight_file,"w+")) as geo_json:
                geo_json.write(json.dumps(json_data,sort_keys=True,ensure_ascii=False,indent=4,separators=(',',':'))) #pretty print

        geoblacklight_file = geoblacklight_file()
        save_pretty()


    def _add_from_responsible_csv(self,json_data): # from updated reponsible party csv, previous workflow is from ISO19139
        originators = self.raw_obj.__dict__["_originators"]
        publishers = self.raw_obj.__dict__["_publishers"]
        owners = self.raw_obj.__dict__["_owners"]

        if originators: json_data['dct_creator_sm'] = originators  # originator, publisher cannot be empty
        if publishers: json_data['dct_publisher_sm'] = publishers
        if owners :json_data['dct_rightsHolder_sm'] = owners


    def _add_from_main_csv(self,json_data):
        def has_original_column(header):
            return (header in par.CSV_HEADER_TRANSFORM)

        def is_multiple_values(header):
            multiple = re.search("_sm|_im$",par.CSV_HEADER_GEOBLACKLIGHT_MAP[header].strip())
            return True if multiple else False

        def need_captilize(header):  # only elements in from csv file needs capitlizsed
            HEADER_UPCASE = ["spatialSubject","subject"]
            return (header in HEADER_UPCASE)

        def d_sub_str(val): # val = "20210407"
            str = val.strip()
            num = len(str)
            try:
                if num == 4:
                    return str
                if num == 6:
                    return datetime.datetime.strptime(str,"%Y%m%d").strftime("%Y-%m")
                if num == 8:
                    return datetime.datetime.strptime(str,"%Y%m%d").strftime("%Y-%m-%d")
            except:
                GeoHelper.arcgis_message("Warning !!!: {0}, 'date_s' value :{2} - in {1}, seems not valid,please check".format(self.geofile,self.arkid,str))
                return str
            GeoHelper.arcgis_message("Warning !!!: {0}, 'date_s' value :{2} - in {1}, may not valid,please check".format(self.geofile,self.arkid,str))
            return str

        def d_time(val):  # add validation
            str = val.strip()
            return datetime.datetime.strptime(str,"%Y%m%d").strftime("%Y-%m-%d") + "T23:34:35.206Z"

        def isoTopics(val):
            codes = val.split("$")
            topics = [par.isoTopic[code] for code in codes]
            return "$".join(topics)

        def correct_val(str,header):
            val = str if str else ""
            if len(val) > 0:
                if header == "modified_date_dt" : val = d_time(val)
                if header == "date_s": val = d_sub_str(val)
                if header == "topicISO": val = isoTopics(val)
                if header == "accessRights_s": val = val.lower().capitalize()
            return val

        def main_csv_column_val(header):
            input_val = self.main_csv_raw[header].strip()
            header_o = "{0}_o".format(header)
            original_val = self.main_csv_raw[header_o].strip() if header_o in self.main_csv_headers else None
            new_val = original_val if (len(input_val)==0 and not original_val) else input_val

            return correct_val(new_val,header)



        def captilize_str(str):
        	noCapWords = ["and", "is", "it", "or","if"]
        	words = [w.capitalize() if (w not in noCapWords) and (w[0].isalpha()) else w  for w in str.split()]
        	return " ".join(words)

        def captilize_arr(header,arr):
            if need_captilize(header):
                return[captilize_str(w) for w in arr]
            return arr

        def format_metadata(header,column_val):
            val = column_val
            if is_multiple_values(header):
                val = column_val.split("$")
                val = captilize_arr(header,val)
            return val

        def add_rights(): # conslidate multiple columns of rights to one
            all_ls = []
            for h in par.CSV_HEADER_COLUMNS_RIGHTS:
                right = main_csv_column_val(h)
                if len(right) > 0:
                    ls = right.split("$")
                    all_ls.extend(ls)
            if len(all_ls)  > 0:
                json_data["dct_rights_sm"] = all_ls

        def add_metadata():
            for header,element_name in par.CSV_HEADER_GEOBLACKLIGHT_MAP.iteritems():
                column_val = main_csv_column_val(header)
                if len(column_val) > 0:
                    meta_value = format_metadata(header,column_val)
                    json_data[element_name] = meta_value

        add_metadata()
        add_rights()


    def _add_from_default(self,json_data):
        json_data["schema_provider_s"] = par.INSTITUTION
        json_data["gbl_mdVersion_s"]   = par.GEOBLACKLGITH_VERSION


    def _add_from_arkid(self,json_data):
        def ref_hosts():
            hosts = par.HOSTS
            hosts_secure = par.HOSTS_SECURE
            access = self.main_csv_raw["accessRights_s"].strip().lower()
            return   hosts if access == "public" else hosts_secure

        def dc_references(arkid): # TODO: add multiple download from csv later
            hosts = ref_hosts()
            id = "{0}{1}".format(par.PREFIX,arkid)
            iso_139_ext = "/iso19139.xml\","
            iso_139_xml = hosts["ISO139"] + id + iso_139_ext
            ref = "{" + hosts["wfs"] + hosts["wms"] + iso_139_xml + hosts["download"] + id + "/data.zip\"}"
            return ref.strip()

        arkid = self.arkid.strip()
        json_data['id'] = "{0}{1}".format(par.PREFIX,arkid)
        json_data['gbl_wxsIdentifier_s'] = arkid
        json_data['dct_identifier_sm'] = ["http://spatial.lib.berkeley.edu/viewpublic/{0}{1}".format(par.PREFIX,arkid)]
        json_data['dct_references_s'] = dc_references(arkid)

    def _add_boundary(self,json_data):
        if os.name == "nt":
            env = None
            geo_type = GeoHelper.geo_type(self.geofile)
            if geo_type == "vector":
                env = self._vector_boundary()
            if geo_type == "raster":
                env = self._raster_boundary()

            if env:
                json_data["locn_geometry"] = env
            else:
                GeoHelper.arcgis_message("{0} - {1}: No boundary found .".format(self.geofile,self.arkid))

    def _raster_boundary(self):
        try:
            raster = arcpy.Raster(self.geofile)
            W = raster.extent.XMin
            E = raster.extent.XMax
            N = raster.extent.YMax
            S = raster.extent.YMin
            return  "ENVELOPE({0},{1},{2},{3})".format(W,E,N,S)  # "ENVELOPE(-122.839783, -122.406402, 38.194766, 37.802318)"
        except:
            return None
        return None

    def _vector_boundary(self):
        try:
            extent = arcpy.Describe(self.geofile).extent
            W = extent.XMin
            E = extent.XMax
            N = extent.YMax
            S = extent.YMin
            return "ENVELOPE({0},{1},{2},{3})".format(W,E,N,S)
        except:
            return None
        return None
