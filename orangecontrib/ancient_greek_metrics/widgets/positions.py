"""
Class Positions
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

import Orange
from Orange.widgets import gui, settings, widget, highcharts

from PyQt4 import QtGui

from LTTL.Table import PivotCrosstab, IntPivotCrosstab
from LTTL.Segmentation import Segmentation
import LTTL.Segmenter as Segmenter
from LTTL.Utils import tuple_to_simple_dict_transpose


from _textable.widgets.TextableUtils import (
    OWTextableBaseWidget,
    InfoBox, 
    SendButton, 
    SegmentationContextHandler,
)

# Parameters
SYLLABLE_ANNOTATION_KEY = 'p'
REFERENCE_ANNOTATION_KEY = 'r'

class HSColumnChart(highcharts.Highchart):
    """
    Extends Highchart and just defines some defaults:
    * enables scroll-wheel zooming,
    * sets the chart type to 'column' 
    """
    def __init__(self, selection_callback, **kwargs):
        super().__init__(enable_zoom=True, chart_type='column', **kwargs)


class Positions(OWTextableBaseWidget):
    """View frequency spectrum as column chart"""
    name = 'Positions'
    description = 'Visualize syllable/letter occurrences at hexametric positions.'
    icon = "icons/positions.svg"

    __version__ = '0.0.1'

    inputs = [('Segmentation', Segmentation, "inputData", widget.Single)]
    outputs = [
        ('Selected verses', Segmentation),
        ('Textable table', PivotCrosstab),
        ('Orange table', Orange.data.Table),
    ]
    
    settingsHandler = SegmentationContextHandler(
        version=__version__.rsplit(".", 1)[0]
    )

    # Settings...
    autoSend = settings.Setting(True)
    queryString = settings.Setting("")
    normalizationMode = settings.ContextSetting("don't normalize")
    annotationKey = settings.ContextSetting("")

    want_main_area = True

    def __init__(self):
        super().__init__()

        self.segmentation = None

        self.infoBox = InfoBox(
            widget=self.controlArea,
            stringClickSend=u", please click 'Send' when ready.",
        )
        self.sendButton = SendButton(
            widget=self.controlArea,
            master=self,
            callback=self.sendData,
            infoBoxAttribute='infoBox',
            buttonLabel=u'Send',
            checkboxLabel=u'Send automatically',
            sendIfPreCallback=self.updateGUI,
        )

        # GUI...

        # Options box
        self.optionsBox = gui.widgetBox(
            widget=self.controlArea,
            box=u'Options',
            orientation='vertical',
            addSpace=True,
        )
        self.queryStringLineEdit = gui.lineEdit(
            widget=self.optionsBox,
            master=self,
            value='queryString',
            orientation='horizontal',
            label=u'Search this syllable/letter:',
            labelWidth=220,
            placeholderText="^\u03C6\u03B1$",
            callback=self.sendButton.settingsChanged,
            tooltip=(
                u"TODO\n"
                u"TODO"
            ),
        )
        gui.separator(widget=self.optionsBox, height=3)
        self.normalizationModeCombo = gui.comboBox(
            widget=self.optionsBox,
            master=self,
            value='normalizationMode',
            sendSelectedValue=True,
            orientation='horizontal',
            label=u'Normalize counts this way:',
            labelWidth=220,
            items=[
                u'based on total syllable number', 
                u'based on total letter number', 
                u"don't normalize",
            ],
            callback=self.sendButton.settingsChanged,
            tooltip=(
                u"TODO\n"
                u"TODO"
            ),
        )
        gui.separator(widget=self.optionsBox, height=3)
        self.annotationCombo = gui.comboBox(
            widget=self.optionsBox,
            master=self,
            value='annotationKey',
            sendSelectedValue=True,
            orientation='horizontal',
            label=u'Group data based on this annotation:',
            labelWidth=220,
            callback=self.sendButton.settingsChanged,
            tooltip=(
                u"Choose the annotation key that will be used to group\n"
                u"data together (each group will have separate counts\n"
                u"in the output)."
            ),
        )
        gui.separator(widget=self.optionsBox, height=3)

        gui.rubber(self.controlArea)

        # Send button...
        self.sendButton.draw()

        # Info box...
        self.infoBox.draw()

        # Create a column chart instance.
        self.line_chart = HSColumnChart(
            selection_callback=None,
            tooltip_shared=True,
            tooltip_useHTML=True,
            tooltip_headerFormat='<span style="font-size:10px">{point.key}</span><table>',
            tooltip_pointFormat='<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
                                '<td style="padding:0"><b>{point.y:.3f}</b></td></tr>',
            tooltip_footerFormat='</table>',
            debug=True
            )
        # Just render an empty chart so it shows a nice 'No data to display'
        # warning
        self.line_chart.chart()

        self.mainArea.layout().addWidget(self.line_chart)

        self.sendButton.sendIf()
        self.adjustSizeWithTimer()

    def inputData(self, segmentation, newId=None):
        """Process incoming data."""
        self.closeContext()
        self.segmentation = segmentation
        self.infoBox.inputChanged()
        if segmentation is not None:
            self.openContext(segmentation)
        self.sendButton.sendIf()

    def sendData(self):
        if self.segmentation is None:
            # Sanity checks failed; nothing to do
            self.send("Selected verses", None)
            self.send("Textable table", None)
            self.send("Orange table", None)
            return
        
        self.replot()
        
        self.send("Selected verses", self.output_segmentation)
        self.send("Textable table", self.output_table)
        self.send("Orange table", self.output_table.to_orange_table())

        self.infoBox.setText(u'Data correctly sent to output.')

        self.sendButton.resetSettingsChangedFlag()

    def updateGUI(self):
        """Update GUI state"""

        self.annotationCombo.clear()

        if self.segmentation is None:
            self.annotationKey = ""
            self.optionsBox.setDisabled(True)
            self.line_chart.clear()
            return
        else:
            annotationKeys = self.segmentation.get_annotation_keys()
            for k in annotationKeys:
                self.annotationCombo.addItem(k)
            if annotationKeys:
                if self.annotationKey not in annotationKeys:
                    self.annotationKey = annotationKeys[0]
            else: 
                self.annotationKey = ""
            self.annotationKey = self.annotationKey
            self.normalizationModeCombo.setDisabled(self.queryString == "")
            self.optionsBox.setDisabled(False)


    def replot(self):

        if self.segmentation is None:
            # Sanity checks failed; nothing to do
            self.send("Selected verses", None)
            self.send("Textable table", None)
            self.send("Orange table", None)
            return

        regex = re.compile(self.queryString)

        total_freq = dict()
        total_freq_pos = dict()
        total_freq_source = dict()
        letter_count = dict()
        freq = dict()

        progressBar = gui.ProgressBar(
            self,
            iterations=2*len(self.segmentation)
        )
        for syllable in self.segmentation:
            pos = syllable.annotations[SYLLABLE_ANNOTATION_KEY]
            source = syllable.annotations[self.annotationKey]
            total_freq[(pos, source)] = total_freq.get((pos, source), 0 )+1
            total_freq_pos[pos] = total_freq.get(pos, 0 ) + 1
            total_freq_source[source] = total_freq.get(source, 0 ) + 1
            if self.queryString:
                content = syllable.get_content()
                freq[(pos, source)] = freq.get((pos, source), 0 ) + len(
                    re.findall(regex, content)
                )
                if self.normalizationMode == 'based on total letter number':
                    letter_count[(pos, source)] =   \
                        letter_count.get((pos, source), 0 ) + len(content)
            progressBar.advance()

        row_ids = list(total_freq_pos.keys())
        col_ids = list(total_freq_source.keys())
        header_row_id = 'source'
        header_row_type = 'string'
        header_col_id = 'pos'
        header_col_type = 'string'
        col_type = dict((k, 'continuous') for k in total_freq_source.keys())

        output_freq = dict()
        table_creator = IntPivotCrosstab
        if self.queryString:
            output_freq.update(freq)
            if (
                   self.normalizationMode == 'based on total syllable number'
                or self.normalizationMode == 'based on total letter number'
            ):
                table_creator = PivotCrosstab
                for row_id in row_ids:
                    for col_id in col_ids:
                        try:
                            key = (row_id, col_id)
                            if self.normalizationMode   \
                                == 'based on total syllable number':
                                output_freq[key] /= total_freq[key]
                            elif self.normalizationMode  \
                                == 'based on total letter number':
                                output_freq[key] /= letter_count[key]
                        except KeyError:
                            pass
        else:
            output_freq.update(total_freq)

        self.output_table = table_creator(
            row_ids,
            col_ids,
            output_freq,
            header_row_id,
            header_row_type,
            header_col_id,
            header_col_type,
            col_type,
            None,
            0,
            None
        ).to_sorted(key_row_id='pos')

        # Plot column chart...
        options = dict(series=[])
        for col_id in col_ids:
            options['series'].append(
                dict(
                    data=tuple_to_simple_dict_transpose(output_freq, col_id).values(), 
                    name=col_id,
                )
            )
        options['yAxis'] = dict(
            title=dict(text='Frequency')
        )           
        options['xAxis'] = dict(
            title=dict(text='Position'),
            categories=row_ids,
            tickmarkPlacement='on',
        )                
        options['plotOptions'] = dict(
            series=dict(
                pointPadding=0.2,
                borderWidth=0,
            )
        )
        kwargs = dict()
        self.line_chart.chart(options, **kwargs)

        if self.queryString:
            base_seg, _ = Segmenter.select(
                self.segmentation, 
                regex,
                progress_callback=progressBar.advance
            )
        else:
            base_seg = self.segmentation
        output_seg = Segmentation(list(), self.segmentation.label)
        for segment in base_seg:
            copied_segment = segment.deepcopy(update=True)
            copied_segment.annotations[REFERENCE_ANNOTATION_KEY]  \
                = segment.annotations[REFERENCE_ANNOTATION_KEY].capitalize()
            output_seg.append(copied_segment)
        
        self.output_segmentation = output_seg

        progressBar.finish()

        
        
    # def send_report(self):
        # self.report_data('Data', self.data)
        # self.report_raw('Scatter plot', self.scatter.svg())


def main():
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    ow = Positions()
    ow.show()
    app.exec_()


if __name__ == "__main__":
    main()