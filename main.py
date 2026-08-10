# Tobey Beer - Holiday Budget Planner
# Last edit: 6 Aug 2026

# Country + city list
from pycountry import countries as cl
from geonamescache import GeonamesCache as gnc

# API
import requests as rq

# Currency data + formatting
from babel.numbers import (
    list_currencies as lc,
    get_territory_currencies as gtc,
    format_currency as fmt,
    LC_MONETARY as lcm,
)

# GUI imports
from PyQt6.QtCore import Qt, QStringListModel as qslm, QDate as qd
from PyQt6.QtWidgets import (
    QApplication as qa,
    QWidget as qw,
    QHBoxLayout as qhbl,
    QVBoxLayout as qvbl,
    QComboBox as qcb,
    QCompleter as qc,
    QLabel as ql,
    QPushButton as qb,
    QCalendarWidget as qcw,
    QTableWidget as qtb,
    QTableWidgetItem as qtwi,
    QStyledItemDelegate as qsid,
    QLineEdit as qle
)
from PyQt6.QtGui import QDoubleValidator as qdv, QIntValidator as qiv

# Other needed imports
from collections import defaultdict
from dateutil.relativedelta import relativedelta as rd
import os
import sys

class scb(qcb): # Searchable dropdown menu/combo box
    def __init__(self):
        super().__init__()
        self.setEditable(True)
        self.setInsertPolicy(qcb.InsertPolicy.NoInsert)
        self.m = qslm(self)
        self.setModel(self.m)
        c = qc(self.m, self)
        c.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        c.setFilterMode(Qt.MatchFlag.MatchContains)
        c.setCompletionMode(qc.CompletionMode.PopupCompletion)
        self.setCompleter(c)

    def si(self, i): # Assumes i will already be a sorted list with no duplicates
        self.m.setStringList(i)
        self.clear()
        self.addItems(i)
        self.setCurrentIndex(-1)
        self.lineEdit().clear()

class ccds(qvbl): # Country + city + date selector
    def __init__(self, h): # h: home?
        super().__init__()
        self.coscb = scb() # Country scb
        self.ciscb = scb() # City scb
        self.curscb = scb() # Currency scb
        self.dt = qcw() # Date select
        self.h = ("Home" if h == True else "Destination")

        self.addWidget(ql(f"{self.h} Country"))
        self.addWidget(self.coscb)
        self.addWidget(ql(f"{self.h} Currency"))
        self.addWidget(self.curscb)
        self.addWidget(ql(f"{self.h} City"))
        self.addWidget(self.ciscb)
        self.addWidget(ql(f"{'Starting' if h == True else 'Finishing'} Date"))
        self.addWidget(self.dt)

        self.coD = {c.name: c.alpha_2 for c in cl} # Country dict
        #print(len(self.coD))
        self.coscb.si(self.coD.keys())
        self.coscb.currentTextChanged.connect(self.occ)

        self.cibc = defaultdict(list) # City by country
        for ci in gnc().get_cities().values():
            if (cc := ci.get("countrycode")) != None and (cn := ci.get("name")) != None:
                self.cibc[cc].append(cn)
        for v in self.cibc.values(): v.sort()

        self.curscb.si(sorted(list(lc())))

        self.dt.setMinimumDate(qd.currentDate())
        self.dt.setVerticalHeaderFormat(qcw.VerticalHeaderFormat.NoVerticalHeader)

    def occ(self, cn): # On country change
        a2 = self.coD.get(cn)
        self.ciscb.si(self.cibc.get(a2, []))
        if a2 == None:
            self.curscb.setCurrentText("")
            return
        
        if len(cc := gtc(a2)) == 0:
            self.curscb.setCurrentText("")
        else:
            self.curscb.setCurrentText(cc[0])

class dd(qsid): # Type checking for table cols 2 and 3 (Double/float delegate)
    def createEditor(self, p, *_):
        e = qle(p)
        v = qdv(bottom=0) # Disallow negatives
        v.setNotation(qdv.Notation.StandardNotation) # Disallow notations such as "1e100"
        e.setValidator(v)
        return e

class id(qsid): # Type checking for table col 2 (Integer delegate)
    def createEditor(self, p, *_):
        e = qle(p)
        e.setValidator(qiv(bottom=0))
        return e

class btbl(qvbl): # Main budgeting table
    def __init__(self):
        super().__init__()
        self.rc = 0 # Current row count
        self.addWidget(ql("Budgeting table"))
        self.tbl = qtb(3,6) # Budgeting table
        self.tbl.setHorizontalHeaderLabels(["Name", "Repeat times", "Unit Cost (---)", "Unit Cost (---)", "Total Cost (---)", "Total Cost (---)"]) # 3 dashes mean no currency selected
        self.tbl.resizeColumnsToContents()
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setItemDelegateForColumn(1, id(self.tbl))
        self.tbl.setItemDelegateForColumn(2, dd(self.tbl))
        self.tbl.setItemDelegateForColumn(3, dd(self.tbl))
        self.tbl.cellChanged.connect(lambda _:self.tbl.resizeColumnsToContents()) # Update col width on cell update
        self.addWidget(self.tbl)

        self.br = qhbl()
        self.arb = qb("Add row") # Self explanatory
        self.arb.clicked.connect(self.ar)
        self.br.addWidget(self.arb)
        self.rrb = qb("Remove row")
        self.rrb.clicked.connect(self.rr)
        self.br.addWidget(self.rrb)

        self.addLayout(self.br)

    def ar(self): # Add row to table
        self.tbl.insertRow(self.rc)
        self.rc += 1

    def rr(self): # Remove row from table
        if (rc := self.tbl.rowCount()) > 1: # Only remove if it doesn't clear the entire table
            self.tbl.removeRow(rc - 1)
            self.rc -= 1

class gui(qw): # Main gui
    def __init__(self):
        super().__init__()
        
        self.ml = qhbl(self) # Main layout
        self.setWindowTitle("Holiday Budget Planner v0.8.5")

        self.col1 = qvbl()
        self.ccb = qhbl()
        self.hcc = ccds(True) # Home country selector
        self.dcc = ccds(False) # Destination country selector
        self.dur = ql("Holiday duration: 0 years, 0 months, 0 days")
        self.ccb.addLayout(self.hcc)
        self.ccb.addLayout(self.dcc)
        self.col1.addLayout(self.ccb)
        self.col1.addWidget(self.dur)

        self.hcc.dt.clicked.connect(self.dcc.dt.setMinimumDate)
        self.dcc.dt.clicked.connect(self.hcc.dt.setMaximumDate)
        # Avoid negative dur and holidays set in past (implicit range check)
        
        self.hcc.dt.clicked.connect(self.udur)
        self.dcc.dt.clicked.connect(self.udur)
        # Note to self: Adding new connections doesn't override prev connections

        self.cr = 0.0 # Conversion rate
        self.crl = ql("Current conversion rate: ---") # Conversion rate label
        self.crl.setToolTip("DISCLAIMER: Past performance is not a reliable indicator of future performance.\nProgram may be subject to floating-point errors.")
        self.col1.addWidget(self.crl)

        self.ml.addLayout(self.col1)
        
        self.btb = btbl()
        self.hcc.curscb.currentIndexChanged.connect(self.ur)
        self.dcc.curscb.currentIndexChanged.connect(self.ur)
        self.hcc.coscb.currentIndexChanged.connect(self.ur) # Link to country scb as well as it is able to silently update curscb
        self.dcc.coscb.currentIndexChanged.connect(self.ur)
        self.col1.addLayout(self.btb)

        #self.btb.tbl.cellChanged.connect(print)
    
    def udur(self): # Update displayed duration of holiday
        diff = rd(self.dcc.dt.selectedDate().toPyDate(), self.hcc.dt.selectedDate().toPyDate())
        self.dur.setText(f"Holiday duration: {diff.years} years, {diff.months} months, {diff.days} days")

    def ur(self): # Update row headers in table and conv rate estimate
        hc = self.hcc.curscb.currentText()
        dc = self.dcc.curscb.currentText()
        lb = ["Name", "Repeat times", f"Unit Cost ({hc or "---"})", f"Unit Cost ({dc or "---"})", f"Holiday Cost ({hc or "---"})", f"Holiday Cost ({dc or "---"})"]
        self.btb.tbl.setHorizontalHeaderLabels(lb)
        self.btb.tbl.cellChanged.connect(lambda _:self.btb.tbl.resizeColumnsToContents())

        try:
            self.cr = rt[dc] / rt[hc]
            self.crl.setText(f"Current conversion rate: {self.cr}")
        except ValueError, KeyError, ZeroDivisionError:
            self.cr = 0.0
            self.crl.setText(f"Current conversion rate: ---")

    def utb(self): # Update table
        pass

errs = { # Different potential error messages
    rq.exceptions.ConnectTimeout: "Could not connect to the server.",
    rq.exceptions.ReadTimeout: "The server connected, but took too long to send data.",
    rq.exceptions.Timeout: "A general timeout error occurred.",
    # To do: Add error messages in case frankfurter changes format. Unsure what these would raise as though (maybe keyerror?)
}

if __name__ == "__main__":
    pth = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rates")
    try:
        res = rq.get(f"https://api.frankfurter.dev/v2/rates?base=AUD", timeout=(5,30)).json() # 5s connect, 30s transfer
        rt = {r["quote"]: r["rate"] for r in res} # Relies on frankfurter not changing format
    except Exception as e:
        print(errs.get(type(e), f"An unknown error has occured: {e}"))
        sys.exit(1)
    #print(rt)
    
    a = qa([]) # Calling with empty list as no args needed
    w = gui()
    w.show()
    
    a.exec()