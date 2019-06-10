#!/usr/bin/env python3
from tkinter import *
from tkinter import messagebox
import configparser
import xml.etree.ElementTree as ET
import grequests
import requests
import grequests
import xmltodict

# main program ################################################################
def main(*args):
    # barcode
    barcode = gui.get_barcode()
    if barcode == "":
        gui.msgbox(barcode, "Bad barcode")
        return
    gui.clear_barcode()
    
    # get item record
    url = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/items?item_barcode="+barcode+"&apikey="+apikey
    r = requests.get(url)
    
    # check for invalid api key
    if r.text == "Invalid API Key":
        gui.msgbox(barcode, "Invalid API Key")
        return
    
    # check for errors
    errors_exist = check_errors_200(r)
    if errors_exist[0] == True:
        error = errors_exist[1]
        gui.msgbox(barcode, error)
        return
    
    # get item values
    item_xml    = r.text
    item       = ET.fromstring(item_xml)
    title      = item.find('bib_data/title').text[:50]
    mms_id     = item.find('bib_data/mms_id').text
    holding_id = item.find('holding_data/holding_id').text
    item_pid   = item.find('item_data/pid').text
    desc       = item.find('item_data/description').text
    
    if desc == None:
        desc = ""    
    
    # other records
    urls = [
        "https://api-na.hosted.exlibrisgroup.com/almaws/v1/bibs/"+mms_id+"?apikey="+apikey,
        "https://api-na.hosted.exlibrisgroup.com/almaws/v1/bibs/"+mms_id+"/holdings?apikey="+apikey,
        "https://api-na.hosted.exlibrisgroup.com/almaws/v1/bibs/"+mms_id+"/holdings/"+holding_id+"/items?limit=10&offset=0&apikey="+apikey,
    ]
    
    r = getXML(urls)
    bib_xml         = r[0].text
    holdings_xml    = r[1].text
    other_items_xml = r[2].text
        
    # check for multiple holdings
    holdings = ET.fromstring(holdings_xml)
    h_dict   = holdings.attrib
    holdings_count = int(h_dict['total_record_count'])
    
    # check for other items
    other_items    = ET.fromstring(other_items_xml)
    item_dict      = other_items.attrib
    items_count = int(item_dict['total_record_count'])
       
    # check if last item and holding on record
    if last_item_check == "active":
        if holdings_count == 1 and items_count == 1:
           gui.msgbox(title, "LAST ITEM ON RECORD")
           return
    
    # add statistics note to item
    if add_item_note == "active":
        item_stat_note = item.find('item_data/'+item_note_field)
        item_stat_note.text = item_note
        
        # make final changes to item
        item_final = ET.tostring(item, encoding="unicode", method="xml")
        url = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/bibs/"+mms_id+"/holdings/"+holding_id+"/items/"+item_pid+"?apikey="+apikey
        r = putXML(url, item_final)
        
        # check for errors
        errors_exist = check_errors_200(r)
        if errors_exist[0] == True:
            error = errors_exist[1]
            gui.msgbox(title, error)
            return
            
    # withdraw item and holdings
    if wd_item == "active":
        url     = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/bibs/"+mms_id+"/holdings/"+holding_id+"/items/"+item_pid+"?override=false&holdings=retain&apikey="+apikey
        headers = {'Content-Type': 'application/xml', 'charset':'UTF-8'}
        r = deleteXML(url)
            
        # check for errors
        errors_exist = check_errors_204(r)
        if errors_exist[0] == True:
            error = errors_exist[1]
            gui.msgbox(title, error)
            return
            
    # finish
    gui.update_status_success(title+" ("+str(desc)+")")

# functions ###################################################################   
def getXML(urls):
    rs = (grequests.get(u) for u in urls)
    r = grequests.map(rs)
    return r

def check_errors_200(r):
    if r.status_code != 200:
        errors = xmltodict.parse(r.text)
        error = errors['web_service_result']['errorList']['error']['errorMessage']
        return True, error
    else: 
        return False, "OK"
        
def check_errors_204(r):
    if r.status_code != 204:
        errors = xmltodict.parse(r.text)
        error = errors['web_service_result']['errorList']['error']['errorMessage']
        return True, error
    else: 
        return False, "OK"

def putXML(url, xml):
    headers = {'Content-Type': 'application/xml', 'charset':'UTF-8'}
    r = requests.put(url, data=xml.encode('utf-8'), headers=headers)
    return r

def deleteXML(url):
    headers = {'Content-Type': 'application/xml', 'charset':'UTF-8'}
    r = requests.delete(url, headers=headers)
    return r    
        
# configurations ##############################################################
config = configparser.ConfigParser()
config.read('config.ini')

apikey                         = config['misc']['apikey']
version                        = config['misc']['version']

last_item_check                = config['checks']['last_item']

item_note_field                = config['stats']['item_note_field'] 
item_note                      = config['stats']['item_note']

add_item_note                  = config['operations']['add_item_note']
wd_item                        = config['operations']['wd_item']

# gui #########################################################################
class gui:
    def __init__(self, master):
        self.master = master
        master.title("Item-Be-Gone "+version)
        master.resizable(0, 0)
        master.minsize(width=600, height=100)
        master.iconbitmap("./images/logo_small.ico")

        logo = PhotoImage(file="./images/logo_large.png")
        self.logo = Label(image=logo)
        self.logo.image = logo
        self.logo.pack()

        self.status_title = Label(height=1, text="Scan barcode to begin.", font="Consolas 12 italic")
        self.status_title.pack(fill="both", side="top")

        self.status_wd = Label(height=1, text="READY", font="Consolas 12 bold", fg="green")
        self.status_wd.pack(fill="both", side="top")

        self.barcode_entry_field = Entry(font="Consolas 16")
        self.barcode_entry_field.focus()
        self.barcode_entry_field.bind('<Key-Return>', main)
        self.barcode_entry_field.pack(fill="both", side="top")
        
        self.scan_button = Button(text="SCAN", font="Arial 16", command=main)
        self.scan_button.pack(fill="both", side="top")
        
    def msgbox(self, title, msg):
        messagebox.showerror("Attention", msg)
        self.update_status_failure(title, msg)
        
    def get_barcode(self):
        barcode = self.barcode_entry_field.get()
        barcode = barcode.replace(" ", "")
        return barcode
        
    def clear_barcode(self):
        self.barcode_entry_field.delete(0, END)
        self.status_title.config(text="")
        self.status_wd.config(text="")
        
    def update_status_success(self, title):
        self.status_title.config(text=title)
        self.status_wd.config(text="SUCCESSFULLY WD", fg="green")
        
    def update_status_failure(self, title, msg):
        self.status_title.config(text=title)
        self.status_wd.config(text=msg, fg="red")
    
root = Tk()
gui = gui(root)
root.mainloop()