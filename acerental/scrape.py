from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import time
import json
import pandas as pd
from flask import Flask, jsonify
import datetime
import re
from flask import request
from multiprocessing import Pool
import copy
from itertools import repeat

MAX_TIMEOUT = 10
ACE_URL = 'https://www.acerentalcars.co.nz/'
app = Flask(__name__)


def parseCarsParallel(ace):
        try:
            cars = WebDriverWait(ace.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
            parsedCars = []
            cars = cars.find_elements_by_class_name("c-vehicle-card")
            totalCars = len(cars)
            req = ace.request
            with Pool() as pool:
                parsedCars = pool.starmap(parseParallelHelper, zip(range(1, totalCars), repeat(req)))
            return parsedCars
        except TimeoutException:
            print("Am i here in time out exception??")
            return parsedCars

def parseParallelHelper(index, request):
        ace = ACE()
        ace.search(request)
        WebDriverWait(ace.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
        parsedCar = {
                    "carName": "",
                    "carType": "",
                    "gearType": "",
                    "maxSeats": "",
                    "maxLuggage": "",
                    "image": "",
                    "carCost": "",
                    "totalCost": "",
                    "currencyCode": "",
                    "insuranceDetails": [],
                    "otherOptions": []
                }
        itemSummary = ace.browser.find_element_by_class_name("l-booking-summary-bar")
        ace.browser.execute_script("arguments[0].style.visibility='hidden'", itemSummary)
        action = ActionChains(ace.browser)
        detailsButton = ace.browser.find_elements_by_class_name("c-vehicle-card")[index].find_element_by_class_name("c-vehicle-card__action")
        action.move_to_element(detailsButton)
        action.click(detailsButton).perform()
        WebDriverWait(ace.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-booking__step"))
        parsedCar = parseCarDetailParallel(ace.browser, parsedCar)
        return parsedCar

def parseCarDetailParallel(browser, parsedCar):
        elements = browser.find_elements_by_class_name("l-booking__step")
        inner = browser.find_element_by_class_name("l-vehicle-panel__inner")
        insuranceDetails = elements[0].find_elements_by_class_name("c-option-card__main")
        otherOptions = elements[1].find_elements_by_class_name("x-option-card__main")
        parsedCar["carName"] = inner.find_element_by_class_name("l-vehicle-panel__subtitle").get_attribute("textContent")
        parsedCar["carType"] = inner.find_element_by_class_name("l-vehicle-panel__title").get_attribute("textContent")
        parsedCar["image"] = inner.find_element_by_class_name("l-vehicle-panel__image").find_element_by_xpath('./img').get_attribute("src")
        

        specifications = inner.find_element_by_class_name("l-vehicle-panel__specifications")
        parsedCar["gearType"] = specifications.find_element_by_xpath('//img[contains(@src, "transmission")]').get_attribute("alt")
        parsedCar["maxSeats"] = specifications.find_element_by_xpath('//img[contains(@src, "passengers")]').get_attribute("alt")
        parsedCar["maxLuggage"] = specifications.find_element_by_xpath('//img[contains(@src, "luggage")]').get_attribute("alt")

        cost = WebDriverWait(browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-vehicle-panel__total"))
        parsedCar["carCost"] = cost.find_element_by_class_name("l-vehicle-panel__total-item-total").get_attribute("textContent")
        totalcost = cost.find_element_by_class_name("l-vehicle-panel__total-price")
        parsedCar["currencyCode"] = totalcost.find_element_by_xpath('./span').get_attribute("textContent")
        parsedCar["totalCost"] = totalcost.get_attribute("textContent")
        for _ins in insuranceDetails:
            insur = {
                "name": _ins.find_element_by_class_name("c-option-card__title").get_attribute("textContent"),
                "price": _ins.find_element_by_class_name("c-option-card__price").get_attribute("textContent")
            }
            parsedCar["insuranceDetails"].append(insur)

        for _opt in otherOptions:
            opt = {
                "title": _opt.find_element_by_class_name("x-option-card__title").get_attribute("textContent"),
                "price": _opt.find_element_by_class_name("x-option-card__price").get_attribute("textContent")
            }
            parsedCar["otherOptions"].append(opt)

        return parsedCar


class ACE():
    def __init__(self):
        options = ChromeOptions()
        #options.add_argument("--headless")
        options.add_argument('--disable-logging')
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        self.browser = Chrome(executable_path='/home/mancunian92/Documents/chromedriver', chrome_options=options)
        self.browser.get(ACE_URL)
        self.searchResults = []
        self.dropDownOptions = []
        self.request = {}
        time.sleep(2)
        self.getDropDownOptions()    
    
    def getDropDownOptions(self):
        self.formOptions = self.browser.find_element_by_name("formPickupLocation")
        self.dropDownOptions = [o.text for o in Select(self.browser.find_element_by_name("formPickupLocation")).options]
 
    def pushDateToBrowser(self, date, diffMonths, isDropOff=False):
        if isDropOff:
            self.browser.find_element_by_id("inline_Dropoff_Date_1").click()
            while(diffMonths > 0):
                self.browser.find_elements_by_class_name("l-form-b__field--datetime")[1].find_element_by_class_name("pika-next").click()
                diffMonths-=1
            tableElem = self.browser.find_elements_by_class_name("l-form-b__field--datetime")[1].find_element_by_class_name("pika-lendar").find_element_by_xpath("./table/tbody")
        else:
            self.browser.find_element_by_id("inline_Pickup_Date_1").click()
            while(diffMonths > 0):
                self.browser.find_elements_by_class_name("l-form-b__field--datetime")[0].find_element_by_class_name("pika-next").click()
                diffMonths-=1
            tableElem = self.browser.find_elements_by_class_name("l-form-b__field--datetime")[0].find_element_by_class_name("pika-lendar").find_element_by_xpath("./table/tbody")
        expr = "./tr/td[@data-day="+ str(date.day) + "]/button"
        tableElem.find_element_by_xpath(expr).click()
    
    def pushTimeToBrowser(self, time, isDropoff = False):
        if isDropoff:
            Select(self.browser.find_element_by_name("formDropoffTime")).select_by_value(time)
        else:
            Select(self.browser.find_element_by_name("formPickupTime")).select_by_value(time)

    def selectDates(self, pickupDateInString, dropOffDateInString, pickupTime, dropOffTime):
        currDate = datetime.datetime.now()
        pickupDate = datetime.datetime.strptime(pickupDateInString, '%d/%b/%Y')
        dropoffDate = datetime.datetime.strptime(dropOffDateInString, '%d/%b/%Y')
        diffMonthsPickup = (pickupDate.year - currDate.year) * 12 + (pickupDate.month - currDate.month)
        diffMonthsDropoff = (dropoffDate.year - pickupDate.year) * 12 + (dropoffDate.month - pickupDate.month)
        self.pushDateToBrowser(pickupDate, diffMonthsPickup)
        self.pushDateToBrowser(dropoffDate, diffMonthsDropoff, isDropOff=True)
        self.pushTimeToBrowser(pickupTime)
        self.pushTimeToBrowser(dropOffTime, isDropoff=True)
     
    def selectLocation(self, pickupLocation, dropOffLocation, isSamePickup = True):
        # First, select the pick up location.
        pickupIndex = self.dropDownOptions.index(pickupLocation)
        Select(self.formOptions).select_by_index(pickupIndex)
        if isSamePickup != True:
            dropOffElem = Select(self.browser.find_element_by_name("formDropoffLocation"))
            dropOffOptions = [o.text for o in dropOffElem.options]
            dropOffIndex = dropOffOptions.index(dropOffLocation)
            dropOffElem.select_by_index(dropOffIndex)
    
    def enterPromocode(self, promoCode):
        self.browser.find_element_by_name("formPromoCode").send_keys(promoCode)

    def search(self, searchRequest):
        pickupDate = searchRequest["pickupDate"]
        dropoffDate = searchRequest["dropDate"]
        pickupLocation = searchRequest["pickupPoint"]
        dropoffLocation = searchRequest["dropPoint"]
        pickupTime = searchRequest["pickupTime"]
        dropoffTime = searchRequest["dropTime"]
        self.selectDates(pickupDate, dropoffDate, pickupTime, dropoffTime)
        self.selectLocation(pickupLocation, dropoffLocation, isSamePickup=False)
        self.browser.find_element_by_class_name("l-hero__booking-action__submit--btn").click()
    
    def parseCars(self, ace):
        try:
            parsedCars = []
            cars = WebDriverWait(self.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
            cars = cars.find_elements_by_class_name("c-vehicle-card")
            totalCars = len(cars)
            for i in range(0,totalCars):
                parsedCar = {
                    "carName": "",
                    "carType": "",
                    "gearType": "",
                    "maxSeats": "",
                    "maxLuggage": "",
                    "image": "",
                    "carCost": "",
                    "totalCost": "",
                    "currencyCode": "",
                    "insuranceDetails": [],
                    "otherOptions": []
                }
                # Hide the itineray summary 
                itemSummary = self.browser.find_element_by_class_name("l-booking-summary-bar")
                self.browser.execute_script("arguments[0].style.visibility='hidden'", itemSummary)
                action = ActionChains(self.browser)
                detailsButton = self.browser.find_elements_by_class_name("c-vehicle-card")[i].find_element_by_class_name("c-vehicle-card__action")
                action.move_to_element(detailsButton)
                action.click(detailsButton).perform()
                WebDriverWait(self.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-booking__step"))
                parsedCar = self.parseCarDetail(self.browser, parsedCar)
                parsedCars.append(parsedCar)
                self.browser.back()
                WebDriverWait(self.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
            return parsedCars
        except TimeoutException:
            print("Am i here in time out exception??")
            return parsedCars

    def parseCarDetail(self, carDetail, parsedCar):
        elements = self.browser.find_elements_by_class_name("l-booking__step")
        inner = carDetail.find_element_by_class_name("l-vehicle-panel__inner")
        insuranceDetails = elements[0].find_elements_by_class_name("c-option-card__main")
        otherOptions = elements[1].find_elements_by_class_name("x-option-card__main")
        parsedCar["carName"] = inner.find_element_by_class_name("l-vehicle-panel__subtitle").get_attribute("textContent")
        parsedCar["carType"] = inner.find_element_by_class_name("l-vehicle-panel__title").get_attribute("textContent")
        parsedCar["image"] = inner.find_element_by_class_name("l-vehicle-panel__image").find_element_by_xpath('./img').get_attribute("src")
        

        specifications = inner.find_element_by_class_name("l-vehicle-panel__specifications")
        parsedCar["gearType"] = specifications.find_element_by_xpath('//img[contains(@src, "transmission")]').get_attribute("alt")
        parsedCar["maxSeats"] = specifications.find_element_by_xpath('//img[contains(@src, "passengers")]').get_attribute("alt")
        parsedCar["maxLuggage"] = specifications.find_element_by_xpath('//img[contains(@src, "luggage")]').get_attribute("alt")

        cost = WebDriverWait(self.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-vehicle-panel__total"))
        parsedCar["carCost"] = cost.find_element_by_class_name("l-vehicle-panel__total-item-total").get_attribute("textContent")
        totalcost = cost.find_element_by_class_name("l-vehicle-panel__total-price")
        parsedCar["currencyCode"] = totalcost.find_element_by_xpath('./span').get_attribute("textContent")
        parsedCar["totalCost"] = totalcost.get_attribute("textContent")
        for _ins in insuranceDetails:
            insur = {
                "name": _ins.find_element_by_class_name("c-option-card__title").get_attribute("textContent"),
                "price": _ins.find_element_by_class_name("c-option-card__price").get_attribute("textContent")
            }
            parsedCar["insuranceDetails"].append(insur)

        for _opt in otherOptions:
            opt = {
                "title": _opt.find_element_by_class_name("x-option-card__title").get_attribute("textContent"),
                "price": _opt.find_element_by_class_name("x-option-card__price").get_attribute("textContent")
            }
            parsedCar["otherOptions"].append(opt)

        return parsedCar


        
        

@app.route("/")
def home():
    return "Scraper Service API"

@app.route("/getPickupLocations")
def getPickupLocations():
    ace = ACE()
    return jsonify({"locations": ace.dropDownOptions})

@app.route("/search", methods={'POST'})
def search():
    req = request.get_json()
    ace = ACE()
    ace.search(req)
    parsed = ace.parseCars(ace)
    return jsonify({"parsed": parsed})

@app.route("/parallelSearch", methods={'POST'})
def searchParallel():
    req = request.get_json()
    ace = ACE()
    ace.request = req
    ace.search(req)
    parsed = parseCarsParallel(ace)
    return jsonify({"parsed": parsed})


if __name__ == "__main__":
    app.run(debug=True)
    # ace = ACE()
    # #ace.enterPromocode("HELLO")
    # ace.search({"pickupPoint": "Perth", "dropPoint": "Sydney", "pickupDate": "20/May/2019", "dropDate": "25/May/2019", "pickupTime": "09:00:00", "dropTime": "15:00:00"})
    # try:
    #     carsDOM = WebDriverWait(ace.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
    #     parsed = ace.parseCars(carsDOM)
    #     print("Parsed is ", parsed)
    # except TimeoutException:
    #     print("Loading took too much time!-Try again")


    