# Tobey Beer - Holiday Budget Planner
# Last edit: 17 Aug 2026

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
from PyQt6.QtCore import (
    Qt, 
    QStringListModel as qslm, 
    QDate as qd,
    QSignalBlocker as qsb,
)

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
    QLineEdit as qle,
    QSizePolicy as qsp,
    QHeaderView as qhv,
    QFileDialog as qfd,
    QMessageBox as qmb,
)

# Other needed imports
from collections import defaultdict
from dateutil.relativedelta import relativedelta as rd
import os
import sys
import json
import ast
import operator as op

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
    def __init__(self, h):
        super().__init__()
        self.coscb = scb() # Country scb
        self.ciscb = scb() # City scb
        self.curscb = scb() # Currency scb
        self.dt = qcw() # Date select
        self.dt.setSizePolicy(qsp.Policy.Ignored, qsp.Policy.Minimum)
        
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

ops = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
} # Could add exponentiation in, doesn't seem like it would be needed though.

def ev(s): # Evaluate simple math functions
    def e(n):
        if type(n) == ast.Constant and type(n.value) in [int, float]:
            return n.value

        if type(n) == ast.BinOp and type(n.op) in ops:
            return ops[type(n.op)](e(n.left), e(n.right))

        if type(n) == ast.UnaryOp and type(n.op) in [ast.UAdd, ast.USub]:
            return e(n.operand) if type(n.op) == ast.UAdd else -e(n.operand)

        raise ValueError

    return e(ast.parse(s, mode="eval").body)


class dd(qsid): # Type checking for table cols 2 and 3 (Double/float delegate)
    def createEditor(self, p, *_):
        return qle(p)

    def setModelData(self, e, m, i):
        try: v = ev(e.text())
        except (ValueError, TypeError, ZeroDivisionError, SyntaxError): return

        if v < 0: return
        m.setData(i, f"{v:g}")

class id(dd): # Type checking for table col 2 (Integer delegate)
    def setModelData(self, e, m, i):
        try: v = ev(e.text())
        except (ValueError, TypeError, ZeroDivisionError, SyntaxError): return

        if v < 0 or not float(v).is_integer(): return
        m.setData(i, str(int(v)))

class btbl(qvbl): # Main budgeting table
    def __init__(self):
        super().__init__()
        self.addWidget(ql("Budgeting table"))
        self.tbl = qtb(3,6) # Budgeting table
        self.tbl.setHorizontalHeaderLabels(["Name", "Repeat times", "Unit Cost (---)", "Unit Cost (---)", "Total Cost (---)", "Total Cost (---)"])

        self.tbl.setAlternatingRowColors(True)

        self.tbl.horizontalHeader().setSectionResizeMode(qhv.ResizeMode.Stretch)

        self.tbl.setItemDelegateForColumn(1, id(self.tbl))
        self.tbl.setItemDelegateForColumn(2, dd(self.tbl))
        self.tbl.setItemDelegateForColumn(3, dd(self.tbl))
        self.addWidget(self.tbl)

        h = self.tbl.horizontalHeader()
        h.setSectionResizeMode(qhv.ResizeMode.ResizeToContents)
        #h.setSectionResizeMode(0, qhv.ResizeMode.Stretch)

        self.br = qhbl()
        self.arb = qb("Add row") # Self explanatory
        self.arb.clicked.connect(self.ar)
        self.br.addWidget(self.arb)
        self.rrb = qb("Remove row")
        self.rrb.clicked.connect(self.rr)
        self.br.addWidget(self.rrb)

        self.addLayout(self.br)

    def ar(self): # Add row to table
        self.tbl.insertRow(self.tbl.rowCount())

    def rr(self): # Remove row from table
        if self.tbl.rowCount() > 1: # Only remove if it doesn't clear the entire table
            self.tbl.removeRow(self.tbl.rowCount() - 1)

class gui(qw): # Main gui
    def __init__(self):
        super().__init__()
        
        self.ml = qhbl(self) # Main layout
        self.setWindowTitle("Holiday Budget Planner v0.8.6")

        self.col1 = qvbl()
        self.ccb = qhbl()
        self.hcc = ccds(True) # Home country selector
        self.dcc = ccds(False) # Destination country selector
        self.dur = ql("Holiday duration: 0 years, 0 months, 0 days")
        self.hcc.addWidget(self.dur)
        self.ccb.addLayout(self.hcc)
        self.ccb.addLayout(self.dcc)
        self.col1.addLayout(self.ccb)

        self.hcc.dt.clicked.connect(self.dcc.dt.setMinimumDate)
        self.dcc.dt.clicked.connect(self.hcc.dt.setMaximumDate)
        # Avoid negative dur and holidays set in past (implicit range check)
        
        self.hcc.dt.clicked.connect(self.udur)
        self.dcc.dt.clicked.connect(self.udur)
        # Note to self: Adding new connections doesn't override prev connections

        self.cr = 0.0 # Conversion rate
        self.crl = ql("Current conversion rate: ---") # Conversion rate label
        self.crl.setToolTip("DISCLAIMER: Past performance is not a reliable indicator of future performance.\nProgram may be subject to floating-point errors.")
        self.dcc.addWidget(self.crl)

        self.ml.addLayout(self.col1)
        
        self.btb = btbl()
        self.hcc.curscb.currentIndexChanged.connect(self.ur)
        self.dcc.curscb.currentIndexChanged.connect(self.ur)
        self.hcc.coscb.currentIndexChanged.connect(self.ur) # Link to country scb as well as it is able to silently update curscb
        self.dcc.coscb.currentIndexChanged.connect(self.ur)
        self.btb.tbl.cellChanged.connect(self.utb)
        self.ml.addLayout(self.btb)
        self.usz()

        self.vcbb = qb("View current budget")
        self.sbb = qb("Save budget to TXT")
        self.vcbb.clicked.connect(self.vcb)
        self.sbb.clicked.connect(self.sb)
        self.hcc.addWidget(self.vcbb)
        self.dcc.addWidget(self.sbb)
    
    def udur(self): # Update displayed duration of holiday
        diff = rd(self.dcc.dt.selectedDate().toPyDate(), self.hcc.dt.selectedDate().toPyDate())
        self.dur.setText(f"Holiday duration: {diff.years} years, {diff.months} months, {diff.days} days")

    def ur(self): # Update row headers in table and conv rate estimate
        hc = self.hcc.curscb.currentText()
        dc = self.dcc.curscb.currentText()
        lb = ["Name", "Repeat times", f"Unit Cost ({hc or "---"})", f"Unit Cost ({dc or "---"})", f"Holiday Cost ({hc or "---"})", f"Holiday Cost ({dc or "---"})"]
        self.btb.tbl.setHorizontalHeaderLabels(lb)

        self.usz()

        try:
            if dc == hc: self.cr = 1.0 # Doing this to minimise FP errs
            else: self.cr = rt[dc] / rt[hc]
            self.crl.setText(f"Current conversion rate: {self.cr}")
        except (ValueError, KeyError, ZeroDivisionError):
            self.cr = 0.0
            self.crl.setText(f"Current conversion rate: ---")

        for r in range(self.btb.tbl.rowCount()):
            if self.rc(r, 2) != None: self.utb(r, 2)
            elif self.rc(r, 3) != None: self.utb(r, 3)

    def rc(self, r, c): # Cell reading helper
        i = self.btb.tbl.item(r, c)

        if i == None or i.text().strip() == "": return None

        try: return float(i.text())
        except ValueError: return None

    def sc(self, r, c, v): # Set cell
        i = self.btb.tbl.item(r, c)

        if i == None:
            i = qtwi()
            self.btb.tbl.setItem(r, c, i)

        i.setText(f"{v:.2f}")

    def utb(self, r, c): # Update table
        self.usz()
        if self.cr <= 0 or c not in [1, 2, 3]: return

        rp = self.rc(r, 1) # Repeat times
        hu = self.rc(r, 2) # Home unit cost
        du = self.rc(r, 3) # Destination unit cost

        # Stop changes from triggering utb again via signal blocker (cause of previous crashing)
        with qsb(self.btb.tbl):
            if c == 2: # Home unit cost was edited
                if hu != None:
                    du = hu * self.cr
                    self.sc(r, 3, du)

            elif c == 3: # Destination unit cost was edited
                if du != None:
                    hu = du / self.cr
                    self.sc(r, 2, hu)

            else: # Repeat count was edited
                if hu != None and du == None: # If only one unit cost exists, fill in the other
                    du = hu * self.cr
                    self.sc(r, 3, du)
                elif du != None and hu == None:
                    hu = du / self.cr
                    self.sc(r, 2, hu)

            if rp != None and hu != None and du != None:
                ht = rp * hu
                dt = rp * du

                self.sc(r, 4, ht)
                self.sc(r, 5, dt)

                for col in (4, 5):
                    i = self.btb.tbl.item(r, col)
                    i.setFlags(i.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.usz()

            else:
                for col in (4, 5):
                    i = self.btb.tbl.item(r, col)
                    if i != None: i.setText("")

    def usz(self):
        self.btb.tbl.resizeColumnsToContents()
        self.btb.tbl.setMinimumWidth(self.btb.tbl.verticalHeader().width() + self.btb.tbl.horizontalHeader().length() + self.btb.tbl.frameWidth()*2)
        self.adjustSize()

    def bt(self): # Budget as text
        # To do: Add validation (ensure all areas are filled out)
        hc = self.hcc.curscb.currentText() or "---"
        dc = self.dcc.curscb.currentText() or "---"


        ht = 0.0
        dt = 0.0

        l = [
            "Holiday Budget",
            f"Home: {self.hcc.coscb.currentText()} - {self.hcc.ciscb.currentText()}",
            f"Destination: {self.dcc.coscb.currentText()} - {self.dcc.ciscb.currentText()}",
            f"Dates: {self.hcc.dt.selectedDate().toString('dd/MM/yyyy')} to {self.dcc.dt.selectedDate().toString('dd/MM/yyyy')}",
            "",
        ]

        for r in range(self.btb.tbl.rowCount()):
            ni = self.btb.tbl.item(r, 0)
            n = ni.text().strip() if ni != None else ""
            rp = self.rc(r, 1)
            hu = self.rc(r, 2)
            du = self.rc(r, 3)
            rh = self.rc(r, 4)
            rd = self.rc(r, 4)

            if n == "" and rp == hu == du == None: continue
            if n == "": continue


            rps = f"{rp:g}" if rp != None else "---"
            hus = f"{hu:.2f}" if hu != None else "---"
            dus = f"{du:.2f}" if du != None else "---"
            rhs = f"{rh:.2f}" if rh != None else "---"
            rds = f"{rd:.2f}" if rd != None else "---"

            l.append(f"{n or f'Item {r + 1}'}: {rps} x {hus} {hc} / {dus} {dc} = {rhs} {hc} / {rds} {dc}")

            if rh != None: ht += rh
            if rd != None: dt += rd

        l += [
            "",
            f"Total: {ht:.2f} {hc}",
            f"Total: {dt:.2f} {dc}",
        ] # To do: Add proper formatting per currency (incl symbols)
        breakpoint()
        return "\n".join(l)

    def vcb(self): # View current budget
        qmb.information(self, "Current budget", self.bt())

    def sb(self): # Save budget
        fn, _ = qfd.getSaveFileName(self, "Save budget", "budget.txt", "Text files (*.txt)")

        if fn == "": return
        if fn.lower().endswith(".txt") == False: fn += ".txt"

        with open(fn, "w", encoding="UTF-8") as f:
            f.write(self.bt())

errs = { # Different potential error messages
    rq.exceptions.ConnectionError: "Could not connect to the server.",
    rq.exceptions.ConnectTimeout: "Could not connect to the server.",
    rq.exceptions.ReadTimeout: "The server connected, but took too long to send data.",
    rq.exceptions.Timeout: "A general timeout error occurred.",
    rq.exceptions.HTTPError: "The server returned an HTTP error.",
    rq.exceptions.JSONDecodeError: "The server returned invalid JSON.",
    ValueError: "Frankfurter returned data in an unexpected format.",
}

if __name__ == "__main__": # Though not needed, it is nice to have
    pth = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rates")
    os.makedirs(pth, exist_ok=True)
    bkp = os.path.join(pth, "bkp.json")

    try:
        res = rq.get("https://api.frankfurter.dev/v2/rates?base=AUD", timeout=(5,30))
        res.raise_for_status()
        res = res.json()

        if type(res) != list: raise ValueError

        for r in res:
            if type(r) != dict: raise ValueError
            if "quote" not in r or "rate" not in r: raise ValueError

        rt = {r["quote"]: float(r["rate"]) for r in res}
        rt["AUD"] = 1.0

        with open(bkp, "w", encoding="UTF-8") as f: json.dump(rt, f)

    except Exception as e:
        print(errs.get(type(e), f"An unknown error has occured: {e}\n{type(e)}"))

        if input("Use fallback conversion rates (Y/N)? ").strip().upper() == "Y":
            with open(bkp, "r", encoding="UTF-8") as f: rt = json.load(f)
        else: sys.exit(1)

    a = qa([])
    w = gui()

    w.adjustSize()
    fg = w.frameGeometry()
    fg.moveCenter(a.primaryScreen().availableGeometry().center())
    w.move(fg.topLeft())

    w.show()
    a.exec()