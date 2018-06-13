"""
Class Positions
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
import codecs

import numpy as np

import Orange
from Orange.widgets import gui, settings, widget

import pyqtgraph as pg

from PyQt4 import QtGui
from PyQt4.QtGui import QFileDialog, QMessageBox

from LTTL.Table import PivotCrosstab, IntPivotCrosstab
from LTTL.Segmentation import Segmentation
import LTTL.Segmenter as Segmenter
from LTTL.Utils import tuple_to_simple_dict_transpose


from _textable.widgets.TextableUtils import (
    OWTextableBaseWidget,
    InfoBox, 
    SendButton, 
    SegmentationContextHandler,
    ProgressBar,
)

# Parameters
SYLLABLE_ANNOTATION_KEY = 'p'
REFERENCE_ANNOTATION_KEY = 'r'

POSITIONS = [
    "1", "10", "11", "12", 
    "2", "20", "21", "22", 
    "3", "30", "31", "32", 
    "4", "40", "41", "42", 
    "5", "50", "51", "52", 
    "6", "60",
]

class myLegend(pg.LegendItem):
    """Subclassing to modify background color..."""
    def paint(self, p, *args):
        p.setPen(pg.functions.mkPen(0, 0, 0)) # outline
        p.setBrush(pg.functions.mkBrush(255, 255, 255, 64))   # background
        p.drawRect(self.boundingRect())
        

class Positions(OWTextableBaseWidget):
    """View frequency spectrum as column chart"""
    name = 'Positions'
    description = 'Visualize syllable/letter occurrences at hexametric positions.'
    icon = "icons/positions.svg"

    __version__ = '0.0.4'

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
    syllInitial = settings.Setting(True)
    syllFinal = settings.Setting(True)
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
            label=u'Search this string:',
            labelWidth=220,
            placeholderText="\u03C6\u03B1",
            callback=self.sendButton.settingsChanged,
            tooltip=(
                u"Enter a string of 1 or more Greek letters here to count\n"
                u"their frequency at each possible hexametric position\n"
                u"(NB: regular expressions are allowed)." 
            ),
        )
        self.searchOptionsBox = gui.indentedBox(
            widget=self.optionsBox,
        )
        gui.checkBox(
            widget=self.searchOptionsBox,
            master=self,
            value='syllInitial',
            label=u'at syllable beginning',
            labelWidth=180,
            callback=self.sendButton.settingsChanged,
            tooltip=(
                u"If this box is checked, the string above will be retrieved\n"
                u"only when it occurs at the beginning of a syllable."
            ),
        )
        gui.checkBox(
            widget=self.searchOptionsBox,
            master=self,
            value='syllFinal',
            label=u'at syllable end',
            labelWidth=180,
            callback=self.sendButton.settingsChanged,
            tooltip=(
                u"If this box is checked, the string above will be retrieved\n"
                u"only when it occurs at the end of a syllable."
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
                u"Choose how to normalize the frequencies (in per mille):\n\n"
                u'- "based on total syllable number" is appropriate in most\n'
                u"  cases\n\n"
                u'- "based on total letter number" can be used when\n'
                u"  searching for individual letters\n\n"
                u'- "don\'t normalize" returns absolute counts'
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

        # Create a bar chart instance...
        stringaxis = pg.AxisItem(orientation='bottom')
        stringaxis.setTicks([dict(enumerate(POSITIONS)).items()])
        self.col_chart = pg.PlotWidget(axisItems={'bottom': stringaxis})
        self.mainArea.layout().addWidget(self.col_chart)      
        
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
            self.col_chart.clear()
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

        queryString = "(?:%s)" % self.queryString
        if self.syllInitial:
            queryString = "^" + queryString
        if self.syllFinal:
            queryString += "$"
            
        regex = re.compile(queryString)

        total_freq = dict()
        total_freq_pos = dict()
        total_freq_source = dict()
        letter_count = dict()
        freq = dict()

        progressBar = ProgressBar(
            self,
            iterations=2*len(self.segmentation)
        )
        self.controlArea.setDisabled(True)
        self.mainArea.setDisabled(True)
        for syllable in self.segmentation:
            pos = syllable.annotations[SYLLABLE_ANNOTATION_KEY]
            source = syllable.annotations[self.annotationKey]
            total_freq[pos, source] = total_freq.get((pos, source), 0)+1
            total_freq_pos[pos] = total_freq.get(pos, 0) + 1
            total_freq_source[source] = total_freq.get(source, 0) + 1
            if self.queryString:
                content = syllable.get_content()
                freq[pos, source] = freq.get((pos, source), 0) + len(
                    re.findall(regex, content)
                )
                if self.normalizationMode == 'based on total letter number':
                    letter_count[pos, source] =   \
                        letter_count.get((pos, source), 0) + len(content)
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
            if self.normalizationMode != "don't normalize":
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
                            output_freq[key] *= 1000 
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
        
        self.col_chart.clear()
        
        try:
            self.legend.scene().removeItem(self.legend)
        except:
            pass
        self.legend = myLegend((100, 70), offset=(-70, 50))
        self.legend.setParentItem(self.col_chart.graphicsItem())
        
        name1 = col_ids[0]
        dist1 = my_tuple_to_simple_dict_transpose(output_freq, name1)
        data1 = [dist1[k] for k in sorted(dist1)]
        s1 = pg.BarGraphItem(
            x=np.arange(len(data1))-0.15,
            height=data1,
            fillLevel=0, 
            fillBrush=(196, 73, 0), 
            brush=(196, 73, 0),
            width=0.3,
        )
        self.col_chart.addItem(s1)
        name2 = col_ids[1]
        dist2 = my_tuple_to_simple_dict_transpose(output_freq, name2)
        data2 = [dist2[k] for k in sorted(dist2)]
        s2 = pg.BarGraphItem(
            x=np.arange(len(data2))+0.15,
            height=data2,
            fillLevel=0, 
            fillBrush=(239, 214, 172),
            brush=(239, 214, 172),
            width=0.3,
        )
        self.col_chart.addItem(s2)
        self.col_chart.setYRange(0, 1.1 * max(data1 + data2), padding=0)
        
        self.legend.addItem(s1, name1)
        self.legend.addItem(s2, name2)
        
        if self.queryString:
            self.col_chart.setTitle(
                "<h2>Freq. of %s at hexametric positions%s</h2>" % (
                    self.queryString,
                    " (in per mille)" 
                        if self.normalizationMode != "don't normalize"
                        else ""
                )
            )
        else:
            self.col_chart.setTitle(
                "<h2>Syllable count at hexametric positions</h2>"
            )

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
        self.controlArea.setDisabled(False)
        self.mainArea.setDisabled(False)
        
    
def my_tuple_to_simple_dict_transpose(my_dict, key):
    simple_dict = tuple_to_simple_dict_transpose(my_dict, key)
    for key in POSITIONS:
        if key not in simple_dict:
            simple_dict[key] = 0
    return simple_dict
    

def main():
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    ow = Positions()
    ow.show()
    app.exec_()


if __name__ == "__main__":
    main()