"""
Class LineChart
Copyright 2017 LangTech Sarl (info@langtech.ch)
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
from Orange.widgets import gui, settings, widget, highcharts

from LTTL.Table import PivotCrosstab
from LTTL.Utils import tuple_to_simple_dict

# Parameters
bin_step    = 5
min_num_bin = 3
max_num_bin = 4
skip_freq_1 = True


class HSLineChart(highcharts.Highchart):
    """
    Extends Highchart and just defines some defaults:
    * enables scroll-wheel zooming,
    * sets the chart type to 'column' 
    """
    def __init__(self, selection_callback, **kwargs):
        super().__init__(enable_zoom=True, chart_type='line', **kwargs)


class Spectrum(widget.OWWidget):
    """View frequency spectrum as column chart"""
    name = 'Spectrum'
    description = 'View frequency spectrum as column chart.'
    icon = "icons/spectrum.svg"

    __version__ = '0.0.2'

    inputs = [("Data", PivotCrosstab, "set_data")]
    outputs = [
        ("Binned data in Textable format", PivotCrosstab),
        ("Binned data in Orange format", Table)
    ]
    
    want_main_area = False

    def __init__(self):
        super().__init__()

        self.data = None

        # Create a column chart instance.
        self.line_chart = HSLineChart(
            selection_callback=None,
            tooltip_shared=True,
            tooltip_useHTML=True,
            tooltip_headerFormat='<span style="font-size:10px">{point.key}</span><table>',
            tooltip_pointFormat='<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
                                '<td style="padding:0"><b>{point.y:.1f} \u2030</b></td></tr>',
            tooltip_footerFormat='</table>',
            debug=True
            )
        # Just render an empty chart so it shows a nice 'No data to display'
        # warning
        self.line_chart.chart()

        self.controlArea.layout().addWidget(self.line_chart)

    def set_data(self, data):
        self.data = data

        # If the data is actually None, we should just reset the plot...
        if data is None:
            self.line_chart.clear()
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

        transposed = self.data.to_transposed()
        options = dict(series=[])

        row_ids = sorted(transposed.row_ids)
        col_ids = sorted(transposed.col_ids)

        # Get frequencies...
        freq = dict()
        for row_id in row_ids:
            freq[row_id] = list(
            tuple_to_simple_dict(transposed.values, row_id).values()
        )

        # Get bins and labels
        lower_bound_bin = 1 + int(skip_freq_1)
        max_lower_bound_bin = bin_step * (max_num_bin-1)
        min_upper_bound_bin = bin_step * min_num_bin + 1
        max_freq = max(transposed.values.values())
        if max_freq > min_upper_bound_bin - bin_step:
            max_bin_limit = max_freq + bin_step + 1
        else:
            max_bin_limit = min_upper_bound_bin + 1
        bins   = [lower_bound_bin]
        labels = list()
        for i in range(bin_step + 1, max_bin_limit, bin_step):
            if i > max_lower_bound_bin + bin_step:
                bins.append(max_bin_limit)
                labels.append('>%i' % (i-bin_step-1))
                break
            bins.append(i)
            labels.append('%i-%i' % (i-bin_step, i-1))
        labels[0] = '%i-%i' % (lower_bound_bin, bin_step)

        # Plot spectrum...
        spectrum = dict()
        n = re.search(r'\d+', transposed.header_row_id).group()
        for row_id in row_ids:
            hist, bins = np.histogram(freq[row_id], bins)
            hist = hist.astype('float_') / sum(freq[row_id]) * 1000
            options['series'].append(dict(data=hist, name=row_id))
            if len(row_ids) == 1:
                row_id = 'proportion of %s-gram types (in per mille)' % n
                row_ids = [row_id]
            for i in range(len(labels)):
                spectrum[(row_id, labels[i])] =  hist[i]
        options['title'] = dict(text='%s-gram frequency spectrum' % n)
        options['yAxis'] = dict(
            title=dict(
                text='proportion of %s-gram types (in per mille)' % n
            )
        )           
        options['xAxis'] = dict(
            title=dict(text='Frequency range'),
            categories=labels,
            tickmarkPlacement='on',
        )           
        
        kwargs = dict()
        self.line_chart.chart(options, **kwargs)

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
        
        
    # def send_report(self):
        # self.report_data('Data', self.data)
        # self.report_raw('Scatter plot', self.scatter.svg())


def main():
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    ow = Spectrum()
    ow.show()
    app.exec_()


if __name__ == "__main__":
    main()