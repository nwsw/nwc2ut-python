import sys, nwctxt

"""Output a report that describes the NWC clip that is passed into this script.

This serves as an effective test for the nwctxt module.
"""

clip = nwctxt.NWC2Clip()
PlayContext = nwctxt.NWC2PlayContext()
for item in clip.Items:
	o = nwctxt.NWC2ClipItem(item)

	print "%s: %s" % (o.GetObjType(), o.GetOpts())

	if o.GetObjType() in ["Note","Chord","RestChord"]:
		namedPitches = []
		poslist = o.GetTaggedOptAsArray("Pos",[]) + o.GetTaggedOptAsArray("Pos2",[])
		for postxt in poslist:
			note = nwctxt.NWC2NotePitchPos(postxt)
			namedPitches.append(PlayContext.GetNotePitchName(note)+PlayContext.GetNotePitchAccidental(note))
		print "NoteNames: %s" % namedPitches

	PlayContext.UpdateContext(o)
	print "PlayContext: %s\n" % PlayContext.Context

sys.exit(nwctxt.NWC2RC_REPORT)
