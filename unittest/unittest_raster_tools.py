#!/usr/bin/python
import os
import sys
import unittest
import shutil


# To test directory layout, go to run: go to run: r_test_0_1_create_resultspace.py

# use date from raster_data/raster - import data
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pre_ingestion import csv_tranform,assign_arks,geodata_workspace,arcgis_iso_export_csv, \
                          validate_csv,validate_geodata,check_projection,zip_data,geo_helper,par,\
                          arcgis_iso_collection,csv_iso_collection,merritt
geo_ext = '.tif'
dirname = os.path.dirname(os.path.abspath(__file__)).replace("unittest","test_data")
raster_original_source = os.path.join(dirname,"raster_data","raster_original_source")
raster_process_path = os.path.join(dirname,"raster_data","raster")
raster_ark_file = os.path.join(raster_process_path ,"arks.txt")
raster_work = os.path.join(raster_process_path,"Work")
raster_source = os.path.join(raster_process_path,"Source")
raster_results = os.path.join(raster_process_path,"Results")
raster_csv = os.path.join(raster_results,par.RESULT_DIRECTORY_PARENTS[0],par.RESULT_DIRECTORY[3])

# A list of output directoies, they are generated by runing "v_test_0_1_create_resultspace.py"
# raster_map = os.path.join(raster_results,par.RESULT_DIRECTORY_PARENTS[0],par.RESULT_DIRECTORY[1])
# raster_download = os.path.join(raster_results,par.RESULT_DIRECTORY_PARENTS[0],par.RESULT_DIRECTORY[0])
# raster_19139 = os.path.join(raster_results,par.RESULT_DIRECTORY_PARENTS[0],par.RESULT_DIRECTORY[4])

def empty_result_dir(dirs):
    for dir in dirs:
        geo_helper.GeoHelper.empty_subpath(dir)

#  Test moving source, allocate ark, export CSV files
#  Fixture: 1) files under raster_original_source; 2) raster_ark_file ;

# Move organize and move original geofiles to work, source directory
class MoveSourceDataToWorkspaceTestCase(unittest.TestCase):
    def setUp(self):
        dirs = [raster_work,raster_source,raster_csv]
        empty_result_dir(dirs)
        self.geoworkspace = geodata_workspace.GeodataWorkspace(raster_original_source,raster_process_path,geo_ext)

    def runTest(self):
        self.geoworkspace.excute()
        geotif_file = os.path.join(raster_work,"2528l","2528l.tif")
        is_file = os.path.isfile(geotif_file)
        self.assertTrue(is_file)

# Assign arks to geofiles under work, source directories
class AllocateArkTestCase(unittest.TestCase):
    def setUp(self):
        self.assign_arks = assign_arks.AssignArks(raster_process_path,raster_ark_file,geo_ext)

    def runTest(self):
        def has_ark_file():
            existed = False
            files_from_work = geo_helper.GeoHelper.files(raster_work)
            for file in files_from_work:
                if file.strip().endswith("_arkark.txt"):
                    existed = True
                    break
            return existed

        self.assign_arks.excute()
        arkfile_existed = has_ark_file()
        self.assertTrue(arkfile_existed)

#1) Move organize and move original geofiles to work, source directory
#2) Assign arks to geofiles under work, source directories
#3) Generate 4 CSV Files under raster_csv
class ExportCsvTestCase(unittest.TestCase):
    def setUp(self):
        dirs = [raster_work,raster_source,raster_csv]
        empty_result_dir(dirs)
        self.geoworkspace = geodata_workspace.GeodataWorkspace(raster_original_source,raster_process_path,geo_ext)
        self.geoworkspace.excute()

        self.assign_arks = assign_arks.AssignArks(raster_process_path,raster_ark_file,geo_ext)
        self.assign_arks.excute()

        workspace_batch_path = geo_helper.GeoHelper.work_path(raster_process_path)
        dest_csv_files = geo_helper.GeoHelper.dest_csv_files(raster_process_path)
        arcGisIso_list = arcgis_iso_collection.ArcGisIsoCollection(workspace_batch_path,geo_ext).all_arcgisiso()
        self.csv = arcgis_iso_export_csv.ExportCsv(arcGisIso_list,dest_csv_files,geo_ext)

    def runTest(self):
        def file_existed(file):
            is_file = os.path.isfile(file)
            self.assertTrue(is_file)

        self.csv.export_csv_files()
        csv_files = [os.path.join(raster_csv,"raster_UPDATE.csv"),os.path.join(raster_csv,"raster_responsible_parties_UPDATE.csv"),\
                     os.path.join(raster_csv,"raster_ORIGINAL.csv"),os.path.join(raster_csv,"raster_responsible_parties_ORIGINAL.csv")]
        for f in csv_files:
            file_existed(f)


# use date from raster_data/raster_export - export data
#  Test fixture files not removed in these directory: 1)updated CSV Files, 2)ISO19139 XML files, 3) GeoFiles in Work Directory, 4) GeoFiles in Source Directory
#  output: 1) Geoblacklgiht json files; 2) map zip files, 3) download data zip files; 3) Merritt manifest ; 0) ISO19139 run code without generating ISO 19139 in local
raster_export_process_path = os.path.join(dirname,"raster_data","raster_export")
raster_export_results = os.path.join(raster_export_process_path,"Results")
exts = par.raster_exts

# Files under these directory are input data:
raster_export_work = os.path.join(raster_export_process_path,"Work")
# raster_export_source = os.path.join(raster_export_process_path,"Source")
raster_export_updated_csv = os.path.join(raster_export_results,par.RESULT_DIRECTORY_PARENTS[0],par.RESULT_DIRECTORY[5])

# output directories
raster_export_map = os.path.join(raster_export_results,par.RESULT_DIRECTORY_PARENTS[0],par.RESULT_DIRECTORY[1])
raster_export_download = os.path.join(raster_export_results,par.RESULT_DIRECTORY_PARENTS[0],par.RESULT_DIRECTORY[0])
raster_export_19139 = os.path.join(raster_export_results,par.RESULT_DIRECTORY_PARENTS[0],par.RESULT_DIRECTORY[4])
raster_export_geoblacklight = os.path.join(raster_export_results,par.RESULT_DIRECTORY_PARENTS[0],par.RESULT_DIRECTORY[2])
raster_export_merritt = os.path.join(raster_export_results,par.RESULT_DIRECTORY_PARENTS[1])

def new_main_csv_file():
    temp_file = os.path.join(raster_export_updated_csv,"template.csv")
    main_file = os.path.join(raster_export_updated_csv,"raster_export_UPDATE.csv")
    geo_helper.GeoHelper.update_main_csv_file(raster_export_work,temp_file,main_file)

class ValidateCsvTestCase(unittest.TestCase):
    def setUp(self):
        self.v_csv = validate_csv.ValidateCSV(raster_export_process_path)
    def runTest(self):
        is_valid = self.v_csv.updated_csv_files_valid()
        self.assertTrue(is_valid)

class TranformISO19139TestCase(unittest.TestCase):
    def setUp(self):
        # Attention !!!!! not to delete files under raster_export_19139 in local, they cannot be created due to the lack of arcpy !!!!
        if os.name == "nt":
            dirs = [raster_export_19139]
            empty_result_dir(dirs)

        self.csvtransform = None
        valid_updated_csv = validate_csv.ValidateCSV(raster_export_process_path)
        if valid_updated_csv.updated_csv_files_existed():
            if valid_updated_csv.updated_csv_files_valid():
                updated_csv_files = geo_helper.GeoHelper.dest_csv_files_updated(raster_export_process_path)
                csv_collection = csv_iso_collection.CsvIsoCollection(updated_csv_files).csv_collection()
                self.csvtransform = csv_tranform.CsvTransform(csv_collection,raster_export_process_path)
    def runTest(self):
        self.csvtransform.transform_iso19139()
        iso19139_file = os.path.join(raster_export_19139,"s7w117","iso19139.xml")
        is_file = os.path.isfile(iso19139_file)
        self.assertTrue(is_file)

class TranformGeoblacklightTestCase(unittest.TestCase):
    def setUp(self):
        dirs = [raster_export_geoblacklight]
        empty_result_dir(dirs)

        self.csvtransform = None
        valid_updated_csv = validate_csv.ValidateCSV(raster_export_process_path)
        if valid_updated_csv.updated_csv_files_existed():
            if valid_updated_csv.updated_csv_files_valid():
                if valid_updated_csv.iso19139_files_existed():
                    updated_csv_files = geo_helper.GeoHelper.dest_csv_files_updated(raster_export_process_path)
                    csv_collection = csv_iso_collection.CsvIsoCollection(updated_csv_files).csv_collection()
                    self.csvtransform = csv_tranform.CsvTransform(csv_collection,raster_export_process_path)
    def runTest(self):
        self.csvtransform.transform_geoblacklight()
        geoblacklight_file = os.path.join(raster_export_geoblacklight,"s7w117","geoblacklight.json")
        is_file = os.path.isfile(geoblacklight_file)
        self.assertTrue(is_file)

class MapZipTestCase(unittest.TestCase):
    def setUp(self):
        dirs = [raster_export_map]
        empty_result_dir(dirs)

        self.zip_data = None
        valid_updated_csv = validate_csv.ValidateCSV(raster_export_process_path)
        if valid_updated_csv.work_files_existed():
            workspace_batch_path = geo_helper.GeoHelper.work_path(raster_export_process_path)
            projected_map_path = geo_helper.GeoHelper.map_download_path(raster_export_process_path)
            self.zip_data = zip_data.ZipData(workspace_batch_path,projected_map_path,"map.zip",exts)

    def runTest(self):
        self.zip_data.map_zipfiles()
        map_zip_file = os.path.join(raster_export_map,"s7w117","map.zip")
        is_file = os.path.isfile(map_zip_file )
        self.assertTrue(is_file)

class DownloadZipTestCase(unittest.TestCase):  # Attention: need second workspace for original data not under it's directory
    def setUp(self):
        dirs = [raster_export_download]
        empty_result_dir(dirs)

        self.zip_data = None
        valid_updated_csv = validate_csv.ValidateCSV(raster_export_process_path)
        if valid_updated_csv.source_files_existed():
            sourcedata_batch_path = geo_helper.GeoHelper.source_path(raster_export_process_path)
            data_download_path = geo_helper.GeoHelper.data_download_path(raster_export_process_path)
            self.zip_data = zip_data.ZipData(sourcedata_batch_path,data_download_path,"data.zip")
    def runTest(self):
        self.zip_data.download_zipfiles()
        data_zip_file = os.path.join(raster_export_download,"s7w117","data.zip")
        is_file = os.path.isfile(data_zip_file )
        self.assertTrue(is_file)

class MerritTestCase(unittest.TestCase):
    def setUp(self):
        dirs = [raster_export_merritt]
        empty_result_dir(dirs)

        self.merritt_collection = None
        valid_updated_csv = validate_csv.ValidateCSV(raster_export_process_path)
        if valid_updated_csv.geoblacklight_files_existed():
            if valid_updated_csv.data_zip_files_existed():
                final_result_path =  geo_helper.GeoHelper.final_result_path(raster_export_process_path)
                self.merritt_collection = merritt.Merrit(raster_export_process_path,final_result_path)
    def runTest(self):
        self.merritt_collection.save_merritt_to_file()
        merritt_file = os.path.join(raster_export_merritt,"merritt.txt")
        is_file = os.path.isfile(merritt_file)
        self.assertTrue(is_file)


if __name__ == '__main__':
    new_main_csv_file()
    unittest.main()
