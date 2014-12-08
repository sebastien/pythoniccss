#!/usr/bin/env python
import texto
import sys ; sys.path.insert(0, ".")

doc  = []
text = open("test-complete.pcss").read()
mode = None

for line in text.split("\n")[:-1]:
	line = line.decode("utf8")
	if "// EOF" in line:
		pass
	elif line.strip().startswith("//"):
		if mode != "T": doc.append("\n")
		doc.append(line.strip()[2:].strip())
		mode = "T"
	elif line.strip():
		if mode != "C": doc.append("\n")
		doc.append(u">\t " + line)
		mode = "C"

open("README.html", "w").write(texto.toHTML(u"\n".join(doc)))
# EOF
