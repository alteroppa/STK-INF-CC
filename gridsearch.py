import pandas as pd
import numpy as np
from statsmodels.tsa.statespace import sarimax as sx
from sklearn.metrics import mean_squared_error
from datetime import timedelta
from dataframes import CallCenter

def getTSeries(callType, bin = "1H", startDay = '8:00', endDay = '18:00'):
    """
    Function created just to get simple time series from our DB
    :param callType: String, type of service to extract
    :param bin: String, size of the "grain" we want to keep, unity measure of the support
    :param startDay: string start of day time in HH:MM
    :param endDay: string end of day time in HH:MM
    :return: time series object
    """
    c = CallCenter()
    #c.callCollection.remove()
    c.cdf = c.dBtoDf()

    data = c.binnedType(c.cdf, callType, bin, startDay, endDay)
    return pd.Series(data['Offered_Calls'], index = data.index)

def MSE(X, sarimax_order, split_date, b_order=None):
    """
    Fits an ARIMA for a given (p,d,q) or
    SARIMAX model for a given (P,D,Q,s), given also a fixed best (p,d,q)
    depending on the number of parameters given (3 or 4)
    :param X: Array of data
    :param sarimax_order: Array of parameters
    :param best_order: Array of best ARIMA(p,d,q)
    :param split_date: date where we stop training and start testing
    :return: Prediction values for test set and Mean Squared Error (and test set)
    """
    # TODO: make sure that best order is either None (non existent, not used) or a list of 3 elements (p,d,q)
    print('here', len(sarimax_order), type(sarimax_order))
    train, test = X[0:split_date], X[split_date:]
    print("train: ", len(train))
    print("test: ", len(test))
    if (len(sarimax_order)) == 3:
        print('sari 3')
        mse = prediction(train, test, a_order = sarimax_order)[1]
    elif len(sarimax_order) == 4:
        print('sari 4')
        mse = prediction(train, test, a_order = b_order, s_order=sarimax_order)[1]
        print(mse)
    else:
        print("Wrong number of parameters!")
    print('error', mse)
    return mse

def prediction(train, test, a_order, s_order=(0,0,0,0)):
    """
    1) predicts observation by observation after fitting on training test
    2) compares prediction with observed value in test set
    3) adds last observed value to training set for nex prediction
    :param train: series/array for training
    :param test: series/array for testing
    :param a_order: array for (p,d,q)
    :param s_order: array for (P,D,Q,s)
    :return: predicted values, error (predicted vs. actual, in the test set)
    """
    # prepare training dataset
    history = [x for x in train]
    predictions = []
    print("predict!")
    print(len(test))
    for t in range((len(test))):
        print(t)
        model = sx.SARIMAX(history, order=a_order, seasonal_order=s_order)
        print("model: done")
        model_fit = model.fit(disp=0)
        yhat = model_fit.forecast()[0]
        predictions.append(yhat)
        print("yhat: ", yhat)
        print("predictions: ", predictions)
        history.append(test[t])
    # calculate out of sample error
    mserror = mean_squared_error(test, predictions)
    print("Error: ", mserror)
    return predictions, mserror

def evaluate_pdq(dataset, p_values, d_values, q_values):
    """
    Evaluates combinations of p, d and q values for an ARIMA model (printing intermediate results)
    :param dataset: Dataset or Series of data
    :param p_values: Array of p values
    :param d_values: Array of d values
    :param q_values: Array of q values
    :return: Best hyperparameters configuration, and minimum MSE of this model
    """
    # dataset = dataset.astype('float32')
    best_score, best_cfg = float("inf"), None
    firstday, lastday = dataset.index.min(), dataset.index.max()
    print(firstday)
    print(lastday)
    daydelta = lastday - firstday
    perc = int(daydelta.days * 0.25)
    newDate = dataset.index.max() - timedelta(days=perc)
    print(newDate)
    for p in p_values:
        for d in d_values:
            for q in q_values:
                arima_order = (p,d,q)
                print("order: ", arima_order)
                try:
                    mse = MSE(dataset, arima_order, newDate)
                    print("got in!")
                    if mse < best_score:
                        print("We got a new best score!")
                        best_score, best_cfg = mse, arima_order
                    print('ARIMA(%s): MSE=%.3f' % (arima_order, mse))
                except:
                    continue
    print('Best model: ARIMA(%s): MSE=%.3f' % (best_cfg, best_score))
    return best_cfg, best_score


def evaluate_PDQs(dataset, P_values, D_values, Q_values, s_values, best_order=(0,0,0)):
    """
    Evaluates combinations of P, D, Q and s values for a SARIMAX model, given the best ARIMA(p,d,q)
    :param dataset: Dataset or Series of data
    :param P_values: Array of P values
    :param D_values: Array of D values
    :param Q_values: Array of Q values
    :param s_values: Array of s values
    :param best_order: Array of 3 elements (p,d,q) that are the best values [given]
    :return: Best hyperparameters configuration, and minimum MSE of this model
    """
    # TODO: make sure best order is a list with 3 elements
    # dataset = dataset.astype('float32')
    best_score, best_cfg = float("inf"), None
    firstday, lastday = dataset.index.min(), dataset.index.max()
    print(firstday)
    print(lastday)
    daydelta = lastday - firstday
    perc = int(daydelta.days * 0.25)
    newDate = dataset.index.max() - timedelta(days=perc)
    print(newDate)
    for P in P_values:
        for D in D_values:
            for Q in Q_values:
                for s in s_values:
                    seasonal_order = (P,D,Q,s)
                    print("order: ", seasonal_order)
                    try:
                        mse = MSE(dataset, seasonal_order, newDate, b_order=best_order)
                        if mse < best_score:
                            print("We got a new best score!")
                            best_score, best_cfg = mse, seasonal_order
                        print('SARIMAX(%s)(%s): MSE=%.3f' % (best_order, seasonal_order, mse))
                    except:
                        continue
    print('Best model: SARIMAX(%s)(%s): MSE=%.3f' % (best_order, best_cfg, best_score))
    return best_cfg, best_score