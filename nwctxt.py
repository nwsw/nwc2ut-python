# -*- coding: latin-1 -*-

r"""A library for processing NoteWorthy Composer clip text.

NoteWorthy Composer (NWC) is a music notation program. All notation objects in
NWC have a text based description that can be copied, pasted, and processed
from the built-in user tool mechanism. The definitions in this module provide
a standard method for drilling into the NWC clip text, analyizing it, changing
it, and then reconstructing the clip in order to send it back into NWC.

This initial alpha version of nwctxt.py is based on the PHP version of the
NWC user tool start kit. The naming conventions are based on the PHP version
of the NWC clip text library. We are considering altering this approach in 
order to make these definitions more consistent with Python standards.

A forum dedicated to NWC2 user tools can be found here:

NoteWorthy Composer > User Tools
http://my.noteworthysoftware.com/?board=7.0

Copyright © 2009 by NoteWorthy Software, Inc.
All Rights Reserved
"""

import string,sys,re,copy

def LibVersion():
	"""Return the version of this library."""
	return "0.1.0"

#################################################################################
# HISTORY:
# ===============================================================================
# [2009-10-05] Initial release 
#################################################################################

NWC2_STARTCLIP = "!NoteWorthyComposerClip"
NWC2_ENDCLIP = "!NoteWorthyComposerClip-End"

# Return codes
NWC2RC_SUCCESS = 0	# Standard output is processed..contents in standard error is presented as a warning
NWC2RC_ERROR = 1	# Standard error is shown to the user
NWC2RC_REPORT = 99	# Standard output is shown to the user

def trigger_error(msg):
	sys.stderr.write(msg)
	sys.exit(NWC2RC_ERROR)

NWC2OPT_RAW = 0
NWC2OPT_TEXT = 1
NWC2OPT_LIST = 2
NWC2OPT_ASSOCIATIVE = 3
#
def NWC2ClassifyOptTag(ObjType,Tag):
	"""Return the expected format for the NWC clip text option.

	All of the top level options in a NWC text object must be of one of the
	following formats:

	NWC2OPT_RAW: Raw text with no conversions or processing
	NWC2OPT_TEXT: The option data should be quoted text
	NWC2OPT_LIST: The option data represents a list of values
	NWC2OPT_ASSOCIATIVE: The option data represents a dictionary of values
	"""
	if (Tag in ["Opts","Dur","Dur2","Endings"]):
		return NWC2OPT_ASSOCIATIVE

	if ((Tag == "Signature") and (ObjType == "Key")):
		return NWC2OPT_ASSOCIATIVE

	if (Tag in ["Text","Name"]):
		return NWC2OPT_TEXT

	if (Tag == "DynVel"):
		return NWC2OPT_LIST

	if ((ObjType in ["Chord","RestChord"]) and (Tag in ["Pos","Pos2"])):
		return NWC2OPT_LIST

	return NWC2OPT_RAW


def EscapeText(s):
	"""Add backslashes to NWC2OPT_TEXT options for passing back to NWC."""
	def replChar(matchobj):
		newchar = matchobj.group(0)
		if (newchar == "\r"): newchar = "r"
		elif (newchar == "\n"): newchar = "n"
		elif (newchar == "\t"): newchar = "t"
		return '\\'+newchar
	return re.sub(r"(['"+r'"\r\n\t\|\\])', replChar, s)

def UnescapeText(s):
	"""Reverse the EscapeText process when processing incoming clip text."""
	def replChar(matchobj):
		newchar = matchobj.group(0)
		if (newchar == "r"): return "\r"
		elif (newchar == "n"): return "\n"
		elif (newchar == "t"): return "\t"
		return newchar[1]
	textr = re.sub(r'\\.', replChar, s)
	return textr

class NWC2Clip:
	"""Load a NWC notation clip into an Items array for further processing.
	"""
	def __init__(self,src=sys.stdin):
		self.Version = ""
		self.Mode = ""
		self.Items = []

		if (isinstance(src,list)):
			self.Items = src
		elif (isinstance(src,file)):
			self.Items = src.readlines()
		elif (isinstance(src,str)):
			if (src.find("\n") < 0):
				self.Items = file(src,'r')
			else:
				self.Items = re.split("\n",src)
			
		if (not isinstance(self.Items,list)):
			trigger_error("Clip text from NoteWorthy Composer 2 is required as input to the NWC2Clip object")

		if (len(self.Items) < 2):
			trigger_error("Format error in the clip text")

		hdr = self.Items.pop(0).strip()

		m = re.match('^'+NWC2_STARTCLIP+r"\(([0-9]+)\.([0-9]+)\,([a-zA-Z0-9_]+)",hdr)
		if (m == None): trigger_error("Unrecognized notation clip format")

		self.Version = m.group(1)+"."+m.group(2)
		self.Mode = m.group(3)

		ftr = False
		while ((ftr != NWC2_ENDCLIP) and (len(self.Items) > 0)):
			ftr = self.Items.pop(-1).strip()

		if (ftr != NWC2_ENDCLIP):
			trigger_error("Could not find clip ending tag")


	def GetClipHeader(self): return NWC2_STARTCLIP + "(" + self.Version + "," + self.Mode + ")"
	def GetClipFooter(self): return NWC2_ENDCLIP


class NWC2ClipItem:
	"""Convert a single line of NWC clip text into an object type and dictionary of options.

	You can pass any single line of NWC clip text into the constructor for this object. The
	resulting object contains a dictionary of all options that appear in the text. You can 
	modify the dictionary in conformance to the standard options for the ObjType, then you
	can call ReconstructClipText to recreate a new line of clip text representing your 
	changes.
	"""
	def __init__(self,itemtext):
		self.ObjType = ""
		self.Opts = {}

		o = re.split(r"(?<!\\)\|",itemtext.rstrip())
		o.pop(0)
		self.ObjType = o.pop(0)
		for v in o:
			m = re.match(R"^([0-9A-Za-z\-_]+):(.*)",v)
			if (m == None): 
				self.Opts[str(v)] = ""
			else: 
				tag = m.group(1)
				optdata = m.group(2).strip()
				tagtype = NWC2ClassifyOptTag(self.ObjType,tag)

				if (tagtype == NWC2OPT_TEXT):
					m = re.match(r"^\"(.*)\"$",optdata)
					if (m != None): optdata = m.group(1)
					optdata = UnescapeText(optdata)
				elif (tagtype == NWC2OPT_LIST):
					optdata = re.split(r"(?<!\\)\,\s*",optdata)
				elif (tagtype == NWC2OPT_ASSOCIATIVE):
					ldata = re.split(r'(?<!\\)\,\s*',optdata)
					optdata = {}
					for ldv in ldata:
						m = re.match(r'^(.+)\=(.*)$',ldv)
						if (m != None): optdata[str(m.group(1))] = m.group(2)
						else: optdata[str(ldv)] = ""

				self.Opts[tag] = optdata

	def GetObjType(self):
		return self.ObjType

	def GetOpts(self):
		return self.Opts

	def GetTaggedOpt(self,tag,nonexistent=False):
		return self.Opts.get(tag,nonexistent)

	def GetTaggedOptAsArray(self,tag,nonexistent=False):
		rv = self.Opts.get(tag)
		if (rv == None): return nonexistent

		if (not isinstance(rv,list)): rv = [ rv ]
		return rv

	def ReconstructClipText(self):
		s = "|"+self.ObjType
		for k,v in self.Opts.iteritems():
			v = self.Opts[k]
			c = NWC2ClassifyOptTag(self.ObjType,k)

			if (v == ""):
				s += "|" + k
				continue

			s += "|" + k + ":"
			optCounter = 0
			if (isinstance(v,str)):
				v2 = EscapeText(v)
				if (c == NWC2OPT_TEXT): s += '"' + v2 + '"'
				else: s += v2
			elif (isinstance(v,int) or isinstance(v,long) or isinstance(v,float)):
				s += v
			elif (isinstance(v,list)):
				if (c != NWC2OPT_LIST): trigger_error("List object ("+k+") referenced an option not set as NWC2OPT_LIST")
				for v2 in v:
					if optCounter: s += ","
					optCounter += 1
					s += v2
			elif (isinstance(v,dict)):
				if (c != NWC2OPT_ASSOCIATIVE): trigger_error("Dictionary object ("+k+") referenced an option not set as NWC2OPT_ASSOCIATIVE")
				for k2,v2 in v.iteritems():
					if optCounter: s += ","
					optCounter += 1
					s += k2
					if (v2 != ""): s += "="+v2

		return s

# Utility code for note pitch
def nwswpy_array_flip(a):
	d ={}
	for i,v in enumerate(a): d[v] = i
	return d

nwcNoteNames = ['A','B','C','D','E','F','G']
nwcNoteKeys = nwswpy_array_flip(nwcNoteNames)
nwcAccidentals = ['v','b','n','#','x']
nwcAccidentalKeys = nwswpy_array_flip(nwcAccidentals)
nwcClefCenterTones = {
	"Treble"	: int((4*7) + nwcNoteKeys['B']),
	"Bass"		: int((2*7) + nwcNoteKeys['D']),
	"Alto"		: int((3*7) + nwcNoteKeys['C']),
	"Tenor"		: int((3*7) + nwcNoteKeys['A']),
	"Drum"		: int((2*7) + nwcNoteKeys['D'])
	}

def nwcGetClefStdCenterTone(clef):
	return nwcClefCenterTones[clef]

class NWC2NotePitchPos:
	"""Create the note pitch position data for the Pos and Pos2 options.
	
	Any Note object has a single Pos option. Any Chord or RestChord has a Pos2
	object. The data associated with the Pos and Pos2 options is provided to 
	this class, in the form of a list.
	"""
	def __init__(self,postxt):
		self.Accidental = ""
		self.Position = 0
		self.Notehead = ""
		self.Tied = ""
	
		m = re.match(r'^([\#bnxv]{0,1})(\-{0,1}[0-9]+)([oxXz]{0,1})([\^]{0,1})',postxt)
		if m != None:
			self.Accidental = m.group(1)
			self.Position = int(m.group(2))
			self.Notehead = m.group(3)
			self.Tied = m.group(4)
		
	def GetAccidentalPitchOffset(self):
		if (self.Accidental): return nwcAccidentalKeys[self.Accidental]-2
		return 0;

	def GetNoteName(self,clef):
		n = 56 + nwcGetClefStdCenterTone(clef) + self.Position
		return nwcNoteNames[n % 7]

	def ReconstructClipText(self):
		s = self.Accidental+str(self.Position)+self.Notehead
		if (self.Tied): s += "^"
		return s


class NWC2PlayContext:
	"""Maintain a virtual play back context while iterating through notation objects.
	"""
	def __init__(self):
		self.Context = {
			"Clef" : "Treble",
			"ClefOctave" : "None",
			"Transposition" : 0,
			"Key" : {'A':0,'B':0,'C':0,'D':0,'E':0,'F':0,'G':0},
			"RunKey" : {'A':0,'B':0,'C':0,'D':0,'E':0,'F':0,'G':0},
			"Ties" : [],
			"Slur" : False
			}

		self.SeenFirstEnding = False
		self.Ending1Context = False

	def SaveRestoreContext(self,o):
		if (o.GetObjType() == "Ending"):
			endings = o.GetTaggedOpt('Endings',{})
			if "1" in endings and not self.SeenFirstEnding:
				self.SeenFirstEnding = True
				self.Ending1Context = copy.deepcopy(self.Context)
			elif self.SeenFirstEnding and not "1" in endings:
				self.Context = copy.deepcopy(self.Ending1Context)

	def GetNotePitchName(self,notepitchObj):
		return notepitchObj.GetNoteName(self.Context["Clef"])

	def GetNotePitchAccidental(self,notepitchObj):
		n = notepitchObj.GetNoteName(self.Context["Clef"])
		a = notepitchObj.Accidental
		if not a: a = nwcAccidentals[self.Context["RunKey"][n]+2]
		return a

	def IsTieReceiver(self,notepitchObj):
		return str(self.GetNotePitchAccidental(notepitchObj)+str(notepitchObj.Position)) in self.Context["Ties"];

	def UpdateContext(self,o):
		if o.GetObjType() in ['Note','Chord','Rest','RestChord']:
			notes = o.GetTaggedOptAsArray("Pos",[])
			notes2 = o.GetTaggedOptAsArray("Pos2",[])
			#
			if notes == []:
				notes = notes2
			elif notes2 != []:
				# Merge the stem down notes with the stem up notes
				if ("Stem" in o.Opts) and (o.Opts["Stem"] == "Up"):
					notes = notes2 + notes
				else:
					notes = notes + notes2

			RunKey_Changes = {}
			for notepitchTxt in notes:
				notepitchObj = NWC2NotePitchPos(notepitchTxt)
				notename = notepitchObj.GetNoteName(self.Context["Clef"])
				noteacc = notepitchObj.Accidental
				if not noteacc: noteacc = nwcAccidentals[self.Context["RunKey"][notename]+2]

				tieKey = noteacc + str(notepitchObj.Position)
				if tieKey in self.Context["Ties"]:
					if not notepitchObj.Tied: self.Context["Ties"].remove(tieKey)
				elif notepitchObj.Tied:
					self.Context["Ties"].append(tieKey)

				if notepitchObj.Accidental:
					RunKey_Changes[notename] = notepitchObj.GetAccidentalPitchOffset()

			self.Context["RunKey"].update(RunKey_Changes)

			if not "Grace" in o.Opts["Dur"]:
				self.Context["Slur"] = "Slur" in o.Opts["Dur"]

		elif o.GetObjType() == "Bar":
				self.Context["RunKey"] = self.Context["Key"].copy()
				if o.GetTaggedOpt("Style","") == "MasterRepeatOpen": 
					self.SeenFirstEnding = False

		elif o.GetObjType() == "Clef":
				self.Context["Clef"] = o.GetTaggedOpt("Type","Treble")
				self.Context["ClefOctave"] = o.GetTaggedOpt("OctaveShift","None")

		elif o.GetObjType() == "Key":
				k = o.GetTaggedOpt('Signature',[])
				for notename in nwcNoteNames:
					a = 0
					if (notename+"b") in k:
						a -= 1
					elif notename+"#" in k:
						a += 1
					self.Context["Key"][notename] = a

				self.Context["RunKey"] = self.Context["Key"].copy()

		elif o.GetObjType() == "Instrument":
				self.Context["Transposition"] = int(o.GetTaggedOpt("Trans",0))

		elif o.GetObjType() == "Ending":
				self.SaveRestoreContext(o)
