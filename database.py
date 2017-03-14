from pymongo import MongoClient
import csv
import json
import pandas as pd
import sys, getopt, pprint

class Database():
    def __init__(self):
        self.data = "res/KS_Mobile_Calls.csv"
        #self.df = pd.read_csv(self.data, delimiter=";", parse_dates=[0])


        self.client = MongoClient()
        self.db = self.client.db
        self.calldb = self.db.callData
        self.ytdb = self.db.YTData

    def clearDB(self, db):
        db.remove()

    def csvToDB(self, csvPath, collection):
        """
        Adds data from csv-file to mongodb. Param could be pandas-df. Index by date?
        :param csvPath: str path to csv-file
        :param db: pymongo collection to add data
        :return:
        """
        df = pd.read_csv(csvPath, delimiter=";", parse_dates=[['Call_Date', 'Time']], nrows=200)
        for date in df['Call_Date_Time']:
            print(date)
            df = df.assign(month=self.addMonth(date))
            #print(date.minute)

        jsonData = json.loads(df.to_json(orient="records"))
        collection.insert_many(jsonData)

    def addMonth(self, dt):
        """
        dt is type datetime.
        takes datetime object, reads month from it, returns list[12] with all '0', except one '1' for the number of the corresponding month
        :param dt:datetime
        :return months:list
        """
        print(dt.month - 1)
        months = [0] * 12
        months[dt.month -1] = 1
        print('months-list:',months)
        return(months)

    def addQuarterlyHour(self, datetime):
        quarters0 = [0] * 24
        quarters1 = [0] * 24
        quarters2 = [0] * 24
        quarters3 = [0] * 24

        if datetime.minute == 0:
            pass

        # numberToAdd = datetime.hour * 4
        # numberToAdd += (datetime.minute % 4)
        # quarters[numberToAdd] = 1
        # return(quarters)


    def addQuarterlyHour(selfs, lineOfDataframe):
        return 'a'



if __name__ == "__main__":
    c = Database()
    c.csvToDB("res/KS_Mobile_Calls.csv", c.calldb)
    #c.clearDB(c.ytdb)
    #c.clearDB(c.calldb)