from pymongo import MongoClient
import csv
import json
import pandas as pd
from datetime import datetime
import sys, getopt, pprint
import matplotlib.pyplot as plt
from matplotlib.dates import DAILY
from ytScraper import YTScraper

plt.style.use('ggplot')

class linRegDB():
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client.db
        self.callCollection = self.db.callData
        self.ytCollection = self.db.YTData

    def clusderDf(self, nrows=None):
        path = "res/KS_Mobile_Calls.csv"
        self.cdf = pd.read_csv(path, delimiter=";", index_col=[0, 1, 4], parse_dates=['Call_Date'], nrows=15000)
        self.cdf.drop('Program', axis=1, inplace=True)
        self.cdf.drop('Service', axis=1, inplace=True)
        self.cdf = self.cdf.groupby(level=[0, 1, 2])["Offered_Calls"].sum()
        levels = ["Call_Date", "Time", "Type"]
        full_idx = pd.MultiIndex.from_product([self.cdf.index.levels[0],
                                               self.cdf.index.levels[1],
                                               self.cdf.index.levels[2]],
                                              names=levels)
        self.cdf = self.cdf.reindex(full_idx.unique()).fillna(0).to_frame()
        self.cdf.index.names = levels

        # combines date and time to datetime
        datelist = self.cdf.index.get_level_values(0)
        hourlist = self.cdf.index.get_level_values(1)
        datelist = (list(map(lambda dfdate, dftime:
                             datetime.combine(dfdate.date(), datetime.strptime(dftime, "%H:%M:%S").time()),
                             datelist, hourlist)))

        self.cdf['Type'] = self.cdf.index.get_level_values('Type')

        self.cdf.index = pd.DatetimeIndex(datelist)
        self.cdf.sort_index(inplace=True)
        # bestillings = self.cdf.loc[self.cdf['Type'] == 'Mobile Bestilling']['Offered_Calls'].tolist()
        # dates = self.cdf.loc[self.cdf['Type'] == 'Mobile Bestilling'].index.get_level_values(0).tolist()

        #creates combined dummy data array and adds it to dataframe
        datetimeFromIndex = self.cdf.index.get_level_values(0).to_datetime()
        dateTimeStrings = []
        for dt in datetimeFromIndex:
            dateTimeStrings.append(dt.strftime("%Y-%m-%d %H:%M:%S"))

        # create datetime string
        self.cdf['dateTimeStrings'] = dateTimeStrings
        self.cdf['combinedDummy']= pd.Series(self.returnCombinedDummyColumn(datetimeFromIndex), index=self.cdf.index) #:Yr[3]+Month[12]+Dayofmonth[31]+Weekday[7]+QuarterlyHours[96]

        self.csvToDB(self.callCollection, self.cdf)

    # def updateCallCollection(self, dataframe, nrows=None):
    #     '''
    #     deletes a collection and re-reads it from csv
    #     :param database: database.[databaseName]
    #     :param collection: database.[databaseName].[collection]
    #     :param nrows: int
    #     '''
    #     self.callCollection.remove()
    #     path = "res/KS_Mobile_Calls.csv"
    #     self.df = pd.read_csv(path, delimiter=";", index_col=[0, 1, 4], parse_dates=['Call_Date'], nrows=nrows)
    #     self.df.drop('Program', axis=1, inplace=True)
    #     self.df.drop('Service', axis=1, inplace=True)
    #     self.addEmptyhour()
    #     self.csvToDB(self.callCollection, self.df)

    def csvToDB(self, collection, df):
        """
        Adds data from csv-file to mongodb. Param could be pandas-df.
        Makes the index multiindex: Call_Date, Time and Type. Drops program.
        :param csvPath: str path to csv-file
        :param db: pymongo collection to add data
        :return:
        """
        self.callCollection.remove()

        # dates = []
        # times = []
        # days = []
        # combined = []
        # years = []
        # for date in df.index.get_level_values(0):
        #     hour = self.addQuarterlyHour(date)
        #     month = self.addMonth(date)[0]
        #     day = self.addMonth(date)[1]
        #     year = self.addMonth(date)[2]
        #     dates.append(month)
        #     days.append(day)
        #     years.append(year)
        #     times.append(hour)
        #
        # for number, item in enumerate(dates):
        #     combined.append(dates[number] + times[number] + days[number] + years[number])
        #
        # df = df.assign(month=dates)
        # df = df.assign(quarterlyHour=times)
        # df = df.assign(weekday=days)
        # df = df.assign(combinedDummy=combined)

        jsonData = json.loads(df.reset_index().to_json(orient="records"))
        collection.insert_many(jsonData)

    # def addMonth(self, dt):
    #     """
    #     takes datetime object, reads month from it, returns list[12] with all '0', except one '1' for the number of the corresponding month
    #     :param dt:datetime
    #     :return months:list
    #     """
    #     #print(dt.year)
    #     day = [0] * 7
    #     day[dt.weekday()] = 1
    #     months = [0] * 12
    #     months[dt.month -1] = 1
    #     year = [0] * 3
    #     dayOfMonth = [0] * 31
    #     if dt.year == 2013:
    #         year[0] = 1
    #     elif dt.year == 2014:
    #         year[1] = 1
    #     elif dt.year == 2015:
    #         year[2] = 1
    #     dayOfMonth[dt.day - 1] = 1
    #     return(months, day, year, dayOfMonth)

    def addQuarterlyHour(self, dt):
        '''
        Transforms string to datetime object, reads hour and minute from it, and creates a 96 bit long list with
            the first 24 bits being the 24 hours with minute == 00, the next 24 bits being the 24 hrs with minute == 15,
            the next 24 bits being the 24 hours with minute == 30 and the last analogue but with minute == 45.
        :param dt: string
        :return: list
        '''
        #newDt = datetime.strptime(dt, "%H:%M:%S") #transforms string to datetime object
        dtObject = dt
        if type(dt) == str:
            dtObject = datetime.strptime(dt, "%H:%M:%S")

        quarters0 = [0] * 24
        quarters1 = [0] * 24
        quarters2 = [0] * 24
        quarters3 = [0] * 24
        hour = dtObject.hour
        minute = dtObject.minute

        if minute == 0:
            quarters0[hour] = 1
        elif minute == 15:
            quarters1[hour] = 1
        elif minute == 30:
            quarters2[hour] = 1
        elif minute == 45:
            quarters3[hour] = 1
        collectedList = quarters0 + quarters1 + quarters2 + quarters3
        return(collectedList)

    # def addEmptyhour(self):
    #     """
    #     Groups the df by Call_date, Time, and Type, and sums the duplicate rows given by the removed subtypes.
    #     Creates a new multiindex with all possible combinations, and combines it with the old one adding 0's for the
    #     missing places.
    #     :return: none
    #     """
    #
    #     self.cdf = self.cdf.groupby(level=[0, 1, 2])["Offered_Calls"].sum()
    #
    #
    #     levels = ["Call_Date", "Time", "Type"]
    #     full_idx = pd.MultiIndex.from_product([self.cdf.index.levels[0],
    #                                            self.cdf.index.levels[1],
    #                                            self.cdf.index.levels[2]],
    #                                           names=levels)
    #
    #     self.cdf = self.cdf.reindex(full_idx.unique()).fillna(0).to_frame()
    #     self.cdf.index.names = levels

    def returnCombinedDummyColumn(self, dtList):
        '''
        combines all content of a liste of datetimes to one long list
        :param colList: mongoDB collection
        :return: list
        '''
        campdf = YTScraper("Telenor")
        campdf = campdf.getDaysSince(self.cdf, 14)

        combinedResult = []
        for dt in dtList:

            funcday = [campdf.loc[dt.date()]["Days in function"]]
            dayssince = [campdf.loc[dt.date()]["Days since campaign"]]

            singleCombined = []
            weekday = [0] * 7
            weekday[dt.weekday()] = 1
            months = [0] * 12
            months[dt.month - 1] = 1 # - 1: returns value between 1 and 12
            dayOfMonth = [0] * 31
            dayOfMonth[dt.day - 1] = 1
            singleCombined += months + dayOfMonth + weekday + self.addQuarterlyHour(dt) + funcday + dayssince
            combinedResult.append(singleCombined)
        print(combinedResult[9])
        print('length of dummy: ', len(combinedResult[9]))

        return combinedResult



if __name__ == "__main__":
    c = linRegDB() # create database.py object
    #c.callCollection.remove()
    c.clusderDf(nrows=None) # read database (with 2000 rows)
    #c.csvToDB(c.callCollection, c.cdf)
    #for line in c.callCollection.find()[0:5]:
    #    print(line)
