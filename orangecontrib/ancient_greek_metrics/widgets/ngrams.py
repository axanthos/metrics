"""
Class NGrams
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

import Orange
from Orange.widgets import gui, settings, widget

from LTTL.Segmentation import Segmentation
from LTTL.Table import Table, IntPivotCrosstab
from _textable.widgets.TextableUtils import (
    OWTextableBaseWidget,
    InfoBox, 
    SendButton, 
    SegmentationContextHandler,
)

# Parameters...
MAX_SEQUENCE_LENGTH = 10


class NGrams(OWTextableBaseWidget):
    """Fast(er) ngram count"""
    name = 'Ngrams'
    description = 'Fast(er) ngram count'
    icon = "icons/NGram.png"

    __version__ = '0.0.1'

    inputs = [('Segmentation', Segmentation, "inputData", widget.Single)]
    outputs = [
        ('Textable detailed table', IntPivotCrosstab, widget.Default),
        ('Orange detailed table', Orange.data.Table),
        ('Textable summary table', IntPivotCrosstab),
        ('Orange summary table', Orange.data.Table),
    ]

    settingsHandler = SegmentationContextHandler(
        version=__version__.rsplit(".", 1)[0]
    )

    # Settings...
    sequenceLength = settings.Setting(1)
    annotationKey = settings.ContextSetting("")

    want_main_area = False
    
    def __init__(self, *args, **kwargs):
        """Initialize an NGram widget"""
        super().__init__(*args, **kwargs)

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
        self.sequenceLengthSpin = gui.spin(
            widget=self.optionsBox,
            master=self,
            value='sequenceLength',
            minv=1,
            maxv=1,
            step=1,
            orientation='horizontal',
            label=u'Count n-gram frequency for n = ',
            labelWidth=220,
            callback=self.sendButton.settingsChanged,
            keyboardTracking=False,
            tooltip=(
                u"Indicate whether to count single segments or\n"
                u"rather sequences of 2, 3, ... segments (n-grams)."
            ),
        )
        gui.separator(widget=self.optionsBox, height=3)
        self.annotationCombo = gui.comboBox(
            widget=self.optionsBox,
            master=self,
            value='annotationKey',
            sendSelectedValue=True,
#            emptyString=u'(none)',
            orientation='horizontal',
            label=u'Group data based on this annotation:',
            labelWidth=220,
            callback=self.sendButton.settingsChanged,
            tooltip=(
                u"Choose the annotation key that will be used to group\n"
                u"data together (each group will have separate counts\n"
                u"in the output tables)."
            ),
        )
        gui.separator(widget=self.optionsBox, height=3)

        gui.rubber(self.controlArea)

        # Send button...
        self.sendButton.draw()

        # Info box...
        self.infoBox.draw()

        self.sendButton.sendIf()
        self.adjustSizeWithTimer()

    def inputData(self, segmentation, newId=None):
        """Process incoming data."""
        self.closeContext()
        self.segmentation = segmentation
        self.infoBox.inputChanged()
        self.updateGUI()
        if segmentation is not None:
            self.openContext(segmentation)
        self.sendButton.sendIf()

    def sendData(self):
        """Check input, compute frequency tables, then send them"""

        # Check that there's something on input...
        if self.segmentation is None:
            self.infoBox.setText(u'Widget needs input.', 'warning')
            self.send('Textable detailed table', None)
            self.send('Orange detailed table', None)
            self.send('Textable summary table', None)
            self.send('Orange summary table', None)
            return

        # Compute n-gram frequencies...
        freq = dict()
        numUnits = dict()
        sequenceLength = self.sequenceLength
        annotationKey = self.annotationKey
        if annotationKey:
            sources = list(
                set(s.annotations[annotationKey] for s in self.segmentation)
            )
        else:
            source  = 'frequency'
            sources = [source]
        progressBar = gui.ProgressBar(
            self,
            iterations=len(self.segmentation) - len(sources)*(sequenceLength-1)
        )
        for source in sources:
            if annotationKey:
                contents = [
                    seg.get_content()
                    for seg in self.segmentation
                    if seg.annotations[annotationKey] == source
                ]
            else:
                contents = [seg.get_content() for seg in self.segmentation]
            source_num_tokens = len(contents)
            source_freq = dict()
            for i in xrange(len(contents)-(sequenceLength-1)):
                seg = tuple(contents[i:i+sequenceLength])
                try:
                    source_freq[seg] += 1
                except:
                    source_freq[seg] = 1
                progressBar.advance()
            source_num_types = len(source_freq)
            if len(sources) == 1:
                source  = 'frequency'
                sources = [source]
            for key, value in source_freq.items():
                freq[(source, ' '.join(key))] = source_freq[key]
            numUnits[(source, u'number of %i-gram tokens' % sequenceLength)] \
                = source_num_tokens
            numUnits[(source, u'number of %i-gram types' % sequenceLength)]  \
                = source_num_types

        # Build detailed table...
        ngrams = list(set(k[1] for k in freq.keys()))
        detailed = IntPivotCrosstab(
            sources,
            ngrams,
            freq,
            u'%i-gram' % sequenceLength,
            u'string',
            u'source',
            u'string',
            dict([(ngram, u'continuous') for ngram in ngrams]),
            None,
            0,
            None,
        )
        
        # Build summary table...
        summary = Table(
            sources,
            [
                u'number of %i-gram tokens' % sequenceLength, 
                u'number of %i-gram types' % sequenceLength,
            ],
            numUnits,
            u'total count',
            u'string',
            u'source',
            u'string',
            {
                u'number of %i-gram tokens' % sequenceLength: u'continuous',
                u'number of %i-gram types' % sequenceLength:  u'continuous',
            },
            None,
            0,
            None,
        )
        
        # Send tables to output
        total = sum([i for i in detailed.values.values()])
        if total == 0:
            self.infoBox.setText(u'Resulting table is empty.', 'warning')
            self.send('Textable detailed table', None)
            self.send('Orange detailed table', None)
            self.send('Textable summary table', None)
            self.send('Orange summary table', None)
        else:
            self.send('Textable detailed table', detailed.to_transposed())
            self.send(
                'Orange detailed table',
                detailed.to_transposed().to_orange_table()
            )
            self.send('Textable summary table', summary)
            self.send('Orange summary table', summary.to_orange_table())

        progressBar.finish()
        self.infoBox.setText(u'Tables correctly sent to output.')

        self.sendButton.resetSettingsChangedFlag()

    def updateGUI(self):
        """Update GUI state"""

        self.annotationCombo.clear()

        if self.segmentation is None:
            self.annotationKey = u''
            self.optionsBox.setDisabled(True)
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
            self.optionsBox.setDisabled(False)
            self.sequenceLengthSpin.setRange(
                1,
                min(MAX_SEQUENCE_LENGTH, len(self.segmentation))
            )
            self.sequenceLength = self.sequenceLength or 1


def main():
    import sys
    from PyQt4.QtGui import QApplication
    # import LTTL.Segmenter as Segmenter
    # from LTTL.Input import Input

    appl = QApplication(sys.argv)
    ow = NGrams()
    # seg1 = Input(u'hello world', label=u'text1')
    # seg2 = Input(u'cruel world', label=u'text2')
    # seg3 = Segmenter.concatenate([seg1, seg2], label=u'corpus')
    # seg4 = Segmenter.tokenize(
        # seg3,
        # [(r'\w+(?u)', u'tokenize', {'type': 'mot'})],
        # label=u'words'
    # )
    # ow.inputData(seg3, 1)
    # ow.inputData(seg4, 2)
    ow.show()
    appl.exec_()
    ow.saveSettings()

if __name__ == "__main__":
    main()