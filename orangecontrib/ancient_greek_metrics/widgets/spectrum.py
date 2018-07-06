"""
Class Spectrum
Copyright 2017-2018 LangTech Sarl (info@langtech.ch)
-----------------------------------------------------------------------------
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import re

import numpy as np

from Orange.data import Table
from Orange.widgets import gui, settings, widget

import pyqtgraph as pg

from PyQt4 import QtGui

from LTTL.Table import PivotCrosstab
from LTTL.Utils import tuple_to_simple_dict

# Parameters
bin_step = 5
min_num_bin = 3
max_num_bin = 4
skip_freq_1 = True


class myLegend(pg.LegendItem):
    """Subclassing to modify background color..."""
    def paint(self, p, *args):
        p.setPen(pg.functions.mkPen(0, 0, 0)) # outline
        p.setBrush(pg.functions.mkBrush(255, 255, 255, 64))   # background
        p.drawRect(self.boundingRect())
        

class Spectrum(widget.OWWidget):
    """View frequency spectrum as column chart"""
    name = 'Spectrum'
    description = 'View frequency spectrum as line chart.'
    icon = "icons/spectrum.svg"

    __version__ = '0.0.5'

    inputs = [("Data", PivotCrosstab, "set_data")]
    outputs = [
        ("Binned data in Textable format", PivotCrosstab),
        ("Binned data in Orange format", Table)
    ]
    
    want_main_area = False

    def __init__(self):
        super().__init__()

        self.data = None

        # Create a line chart instance...
        self.line_chart = pg.PlotWidget()
        self.controlArea.layout().addWidget(self.line_chart)

    def set_data(self, data):
        self.data = data

        # If the data is actually None, we should just reset the plot...
        if data is None:
            # self.line_chart.clear()
            self.send("Binned data in Textable format", None)
            self.send("Binned data in Orange format", None)
            return

        # ... else replot.
        self.replot()

    def replot(self):

        if self.data is None:
            # Sanity checks failed; nothing to do
            self.send("Binned data in Textable format", None)
            self.send("Binned data in Orange format", None)
            return

        self.line_chart.clear()
        
        transposed = self.data.to_transposed()

        row_ids = sorted(transposed.row_ids)
        col_ids = sorted(transposed.col_ids)

        # Get frequencies...
        freq = dict()
        for row_id in row_ids:
            freq[row_id] = [
                f for f in tuple_to_simple_dict(
                    transposed.values, row_id
                ).values()
                if f > 0
            ]

        # Get bins and labels
        lower_bound_bin = 1 + int(skip_freq_1)
        max_lower_bound_bin = bin_step * (max_num_bin-1)
        min_upper_bound_bin = bin_step * min_num_bin + 1
        max_freq = max(transposed.values.values())
        if max_freq > min_upper_bound_bin - bin_step:
            max_bin_limit = max_freq + bin_step + 1
        else:
            max_bin_limit = min_upper_bound_bin + 1
        bins = [lower_bound_bin]
        labels = list()
        for i in range(bin_step+1, max_bin_limit, bin_step):   
            if bin_step > 1:
                labels.append('%i-%i' % (i-bin_step, i-1))
            else:
                labels.append('%i' % (i-1))            
            if i > max_lower_bound_bin + bin_step:
                bins.append(max_bin_limit)
                break
            bins.append(i)
        if skip_freq_1:
            labels[0] = re.sub(r"\b1\b", r"2", labels[-0])
        labels[-1] = re.sub(r"(\d+).*", r"\1+", labels[-1])
        if bins[0] == bins[1]:
            bins.pop(0)
            labels.pop(0)
        self.line_chart.getAxis('bottom').setTicks([enumerate(labels)])
        
        # Plot spectrum...
        try:
            self.legend.scene().removeItem(self.legend)
        except:
            pass
        all_spectrums = list()
        self.legend = myLegend((100, 70), offset=(-70, 50))
        self.legend.setParentItem(self.line_chart.graphicsItem())
        spectrum = dict()
        n = re.search(r'\d+', transposed.header_row_id).group()
        for idx, row_id in enumerate(row_ids):
            hist, bins = np.histogram(freq[row_id], bins)
            hist = hist.astype('float_')      \
                / len(freq[row_id]) * 1000
            all_spectrums += list(hist)
            pen=pg.mkPen(
                pg.intColor(
                    idx, 
                    hues=len(row_ids), 
                    minValue=32, 
                    maxValue=224,
                ),
                width=2, 
            )
            line = self.line_chart.plot(
                hist, 
                pen=pen,
            )
            self.legend.addItem(line, row_id)
            if len(row_ids) == 1:
                row_id = 'proportion of %s-gram types (in per mille)' % n
                row_ids = [row_id]
            for i in range(len(labels)):
                spectrum[(row_id, labels[i])] = hist[i]
        self.line_chart.setTitle("<h2>%s-gram frequency spectrum</h2>" % n)
        self.line_chart.setLabel(
            "left", 
            "<h3>proportion of %s-gram types (in per mille)</h3>" % n,
        )
        self.line_chart.setLabel("bottom", "<h3>Frequency range</h3>")

        # Build and send table...
        output_table = PivotCrosstab(
            row_ids,
            labels,
            spectrum,
            u'frequency range',
            u'string',
            u'source',
            u'string',
            dict([(label, u'continuous') for label in labels]),
            None,
            0,
            None,
        )

        self.send("Binned data in Textable format", output_table)
        self.send("Binned data in Orange format", output_table.to_orange_table())
        
        

def main():
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    ow = Spectrum()
    ow.show()
    app.exec_()


if __name__ == "__main__":
    main()