# PPPPPP          FFFFFFF        iii lll 333333  
# PP   PP yy   yy FF       oooo      lll    3333 
# PPPPPP  yy   yy FFFF    oo  oo iii lll   3333  
# PP       yyyyyy FF      oo  oo iii lll     333 
# PP           yy FF       oooo  iii lll 333333  .1
#         yyyyy                                                   
# Airfoiltools.com .dat downloader

import os
from os import path
import re
import subprocess as sub
import requests
import csv
from bs4 import BeautifulSoup

aft_url = 'http://airfoiltools.com/airfoil/seligdatfile?airfoil='
directory = os.getcwd() + '\dat\\'

if not os.path.exists(directory):
    os.makedirs(directory)

def get_foil_list():
    foil_list = []
    url = 'http://m-selig.ae.illinois.edu/ads/coord_seligFmt/'
    data = requests.get(url)
    soup = BeautifulSoup(data.text,'lxml')
    tabl = soup.find('table')
    rows = tabl.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        nam = cols[1].split('.')[0] if len(cols) == 5 else 'index'

        foil_list.append(nam) if nam != 'index' else None
    return foil_list[1::]

def get_foils():
    foil_list = get_foil_list()
    for items in foil_list:
        dat_file = directory + items + '.dat'
        if not os.path.isfile(dat_file):
            req = requests.get(aft_url + items + '-il').text
            if '<!DOCTYPE' in req or 'Error' in req or 'error' in req:
                print(items + ' not found on AirfoilTools, skipping')
                continue
            file = open(dat_file, 'w')
            file.write(req)
            print(items + ' foil saved')
            file.close()
        else:
            print(items + ' already exists')

def xfoil(re):
    foil_list = get_foil_list()
    reynolds_number = str(re)
    pol_dir = 'pol\\' + reynolds_number
    if not os.path.exists(pol_dir):
        os.makedirs(pol_dir)
    for items in foil_list:
        dat_file = 'dat\\' + items + '.dat'
        if not os.path.isfile(dat_file):
            print(items + ' dat file missing, skipping')
            continue
        pol_file = pol_dir + '\\' + items + '.pol'
        comm  = "load " + dat_file + "\n"
        comm += "oper\n"
        comm += "iter 70\n"
        comm += "vpar\n"
        comm += "n 9\n"
        comm += "\n"
        comm += "visc " + reynolds_number + "\n"
        comm += "pacc\n"
        comm += pol_file + "\n"
        comm += "\n"
        comm += "aseq -5 20 0.5\n"
        comm += "pacc\n"
        comm += "\n"
        comm += "quit\n"
        ps = sub.Popen(
            ['xfoil.exe'],
            stdin=sub.PIPE,
            stdout=sub.PIPE,
            stderr=sub.PIPE,
            encoding='UTF-8'
        )
        try:
            outs, errs = ps.communicate(comm, timeout=15)
        except sub.TimeoutExpired:
            ps.kill()
            outs, errs = ps.communicate()
        print(items + ' processed')

def process_dat(reynolds_number):
    foil_list = get_foil_list()
    for item in foil_list:
        print(f"trying {item}")
        try:
            file = open('pol\\' + reynolds_number + '\\' + item + '.pol','r')
        except FileNotFoundError:
            continue
        alpha = []
        cl = []
        cd = []
        cdp = []
        cm = []
        top_xtr = []
        bot_xtr = []
        for index, line in enumerate(file):
            if "xtrf =" in line:
                xtrf_top = float(line[10:15])
                xtrf_bottom = float(line[29:34])
            elif "Mach =" in line:
                mach = float(line[10:15])
                re_str = line[29:38]
                re = float(re_str.replace(" ",""))
                ncrit = float(line[52:58])
            elif index >= 12 and line != "":
                alpha.append(float(str.strip(line[2:8])))
                cl.append(float(str.strip(line[9:17])))
                cd.append(float(str.strip(line[18:27])))
                cdp.append(float(str.strip(line[28:37])))
                cm.append(float(str.strip(line[38:46])))
                top_xtr.append(float(str.strip(line[47:55])))
                bot_xtr.append(float(str.strip(line[56:64])))
        # Thickness
        # Geometry parsing
        response = sub.run("xfoil.exe", input="load dat\\" + item + ".dat\nquit\n", stdout=sub.PIPE, shell=False, encoding='UTF-8', timeout=10, creationflags=sub.CREATE_NO_WINDOW)
        output_string = response.stdout
        thickness = None
        camber = None
        thickness_pt = None
        camber_pt = None
        leading_x = None
        leading_y = None
        trailing_x = None
        trailing_y = None
        chord = None
        coordinate_pts = None
        for line in output_string.splitlines():
            if 'Number of input coordinate points' in line:
                try:
                    coordinate_pts = int(line.strip().split()[-1])
                except:
                    pass
            elif 'Max thickness' in line:
                try:
                    parts = line.split()
                    thickness = round(float(parts[3]), 7)
                    thickness_pt = round(float(parts[6]), 7)
                except:
                    pass
            elif 'Max camber' in line:
                try:
                    parts = line.split()
                    camber = round(float(parts[3]), 7)
                    camber_pt = round(float(parts[6]), 7)
                except:
                    pass
            elif 'LE  x,y' in line:
                try:
                    parts = line.replace('|','').split()
                    leading_x = round(float(parts[3]), 7)
                    leading_y = round(float(parts[4]), 7)
                    chord = round(float(parts[7]), 7)
                except:
                    pass
            elif 'TE  x,y' in line:
                try:
                    parts = line.replace('|','').split()
                    trailing_x = round(float(parts[3]), 7)
                    trailing_y = round(float(parts[4]), 7)
                except:
                    pass
        if any(v is None for v in [thickness, camber, leading_x, trailing_x, chord]):
            print(f"{item} geometry incomplete, skipping")
            continue
        with open('csv\\' + reynolds_number + '\\' + item + '.csv', 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile, dialect='excel')
            csvwriter.writerow(['Xtrf_top', xtrf_top])
            csvwriter.writerow(['Xtrf_bottom', xtrf_bottom])
            csvwriter.writerow(['Mach (0)', mach])
            csvwriter.writerow(['Re', re])
            csvwriter.writerow(['Ncrit', ncrit])
            csvwriter.writerow(['# of coord points', coordinate_pts])
            csvwriter.writerow(['Thickness', thickness])
            csvwriter.writerow(['Thickness point', thickness_pt])
            csvwriter.writerow(['Camber', camber, camber_pt])
            csvwriter.writerow(['Leading edge', leading_x, leading_y])
            csvwriter.writerow(['Trailing edge', trailing_x, trailing_y])
            csvwriter.writerow([])
            csvwriter.writerow(['Alpha','CL','CD','CDp','CM','Top_Xtr','Bot_Xtr'])
            for a, items in enumerate(alpha):
                csvwriter.writerow([alpha[a],
                                    cl[a],
                                    cd[a],
                                    cdp[a],
                                    cm[a],
                                    top_xtr[a],
                                    bot_xtr[a]])
        file.close()
        print(item, "complete")
    
# xfoil('1e5')          
# xfoil('2e5')
# xfoil('3e5')
# xfoil('4e5')
# xfoil('5e5')
# xfoil('6e5')
# xfoil('7e5')
# xfoil('8e5')
# xfoil('9e5')
# xfoil('1e6')
# process_dat('1e5')
# process_dat('2e5')
#process_dat('3e5')
#process_dat('4e5')
#process_dat('5e5')
#process_dat('6e5')
#process_dat('7e5')
#process_dat('8e5')
#process_dat('9e5')
#process_dat('1e6')

get_foils()
xfoil('1e6')
process_dat('1e6')