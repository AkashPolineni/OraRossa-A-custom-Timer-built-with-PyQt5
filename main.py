import sys
from PyQt5.QtWidgets import QApplication
from ui import OraRossa

app = QApplication(sys.argv)
window = OraRossa()
window.show()
sys.exit(app.exec_())