from phBot import *
import QtBind
import struct
import json
import os

pName = 'xTargetSupport'
pVersion = '1.2.3'
pUrl = 'https://raw.githubusercontent.com/JellyBitz/phBot-xPlugins/master/xTargetSupport.py'

# ______________________________ Initializing ______________________________ #

# globals
character_data = None

# Initializing GUI
gui = QtBind.init(__name__,pName)
cbxEnabled = QtBind.createCheckBox(gui,'cbxDoNothing','Enabled',6,9)
cbxDefensive = QtBind.createCheckBox(gui,'cbxDoNothing','Defensive Mode',85,9)

QtBind.createLabel(gui,'* Leader list',11,35)
tbxLeaders = QtBind.createLineEdit(gui,"",6,51,100,20)
lvwLeaders = QtBind.createList(gui,6,72,176,60)
btnAddLeader = QtBind.createButton(gui,'btnAddLeader_clicked',"    Add    ",107,50)
btnRemLeader = QtBind.createButton(gui,'btnRemLeader_clicked',"     Remove     ",55,131)

# ______________________________ Methods ______________________________ #

# Return folder path
def getPath():
	return get_config_dir()+pName+"\\"

# Return character configs path (JSON)
def getConfig():
	return getPath()+character_data['server'] + "_" + character_data['name'] + ".json"

# Check if character is ingame
def isJoined():
	global character_data
	character_data = get_character_data()
	if not (character_data and "name" in character_data and character_data["name"]):
		character_data = None
	return character_data

# Load default configs
def loadDefaultConfig():
	# Clear data
	QtBind.setChecked(gui,cbxEnabled,False)
	QtBind.clear(gui,lvwLeaders)
	QtBind.setChecked(gui,cbxDefensive,False)

# Loads all config previously saved
def loadConfigs():
	loadDefaultConfig()
	if isJoined():
		# Check config exists to load
		if os.path.exists(getConfig()):
			data = {}
			with open(getConfig(),"r") as f:
				data = json.load(f)
			if "Leaders" in data:
				for charName in data["Leaders"]:
					QtBind.append(gui,lvwLeaders,charName)
			if "Defensive" in data and data['Defensive']:
				QtBind.setChecked(gui,cbxDefensive,True)

# Return True if text exist at the list
def ListContains(text,lst):
	text = text.lower()
	for i in range(len(lst)):
		if lst[i].lower() == text:
			return True
	return False

# Add leader to the list
def btnAddLeader_clicked():
	if character_data:
		player = QtBind.text(gui,tbxLeaders)
		# Player nickname it's not empty
		if player and not ListContains(player,QtBind.getItems(gui,lvwLeaders)):
			# Init dictionary
			data = {}
			# Load config if exist
			if os.path.exists(getConfig()):
				with open(getConfig(), 'r') as f:
					data = json.load(f)
			# Add new leader
			if not "Leaders" in data:
				data['Leaders'] = []
			data['Leaders'].append(player)
			# Replace configs
			with open(getConfig(),"w") as f:
				f.write(json.dumps(data, indent=4, sort_keys=True))
			QtBind.append(gui,lvwLeaders,player)
			QtBind.setText(gui,tbxLeaders,"")
			log('Plugin: Leader added ['+player+']')

# Remove leader selected from list
def btnRemLeader_clicked():
	if character_data:
		selectedItem = QtBind.text(gui,lvwLeaders)
		if selectedItem:
			if os.path.exists(getConfig()):
				data = {"Leaders":[]}
				with open(getConfig(), 'r') as f:
					data = json.load(f)
				try:
					# remove leader nickname from file if exists
					data["Leaders"].remove(selectedItem)
					with open(getConfig(),"w") as f:
						f.write(json.dumps(data, indent=4, sort_keys=True))
				except:
					pass # just ignore file if doesn't exist
			QtBind.remove(gui,lvwLeaders,selectedItem)
			log('Plugin: Leader removed ['+selectedItem+']')

# Return character name from player ID but only if is in party
def getCharName(UniqueID):
	# Load all players from party
	players = get_party()
	
	# Checking if UID is mine
	if UniqueID == character_data['player_id']:
		return character_data['name']
	
	# Check the UID with all players
	if players:
		for key, player in players.items():
			if player['player_id'] == UniqueID:
				return player['name']
	return ""

# Inject Packet - Select Target
def Inject_SelectTarget(targetUID):
	p = struct.pack('<I',targetUID)
	inject_joymax(0x7045,p,False)

# ______________________________ Events ______________________________ #

# Called when the character enters the game world
def joined_game():
	loadConfigs()

# Called after teleporting
def teleported():
	global character_data
	# update uid on teleported
	character_data = get_character_data()

# All packets received from game server will be passed to this function
# Returning True will keep the packet and False will not forward it to the game client
def handle_joymax(opcode, data):
	# Object skill action & Enabled xTargetSupport
	if opcode == 0xB070 and QtBind.isChecked(gui,cbxEnabled):
		# Success
		if data[0] == 1:
			skillType = data[1] # 2 = Attack
			index = 7
			attackerUID = struct.unpack_from("<I",data,index)[0]
			index += 8
			locale = get_locale()
			if locale == 18 or locale == 56: # iSRO & TRSRO
				index += 4
			targetUID = struct.unpack_from("<I",data,index)[0]
			# Check attack types only
			if skillType == 2:
				# Check the nickname from attacker
				charName = getCharName(attackerUID)
				if charName and ListContains(charName,QtBind.getItems(gui,lvwLeaders)):
					log("Plugin: Targetting enemy from "+charName)
					Inject_SelectTarget(targetUID)
				elif QtBind.isChecked(gui,cbxDefensive):
					# Check the nickname from target
					charName = getCharName(targetUID)
					if charName and ListContains(charName,QtBind.getItems(gui,lvwLeaders)):
						log("Plugin: Targetting attacker from "+charName)
						Inject_SelectTarget(attackerUID)
	return True

# All chat messages received are sent to this function
def handle_chat(t,charName,msg):
	if charName:
		if msg.startswith("TARGET "):
			# Check player at leader list
			if ListContains(charName,QtBind.getItems(gui,lvwLeaders)):
				# Read next param
				msg = msg[7:]
				if msg == "ON":
					QtBind.setChecked(gui,cbxEnabled,True)
				elif msg == "OFF":
					QtBind.setChecked(gui,cbxEnabled,False)

# Plugin loaded
log('Plugin: '+pName+' v'+pVersion+' succesfully loaded')

if os.path.exists(getPath()):
	# Adding RELOAD plugin support
	loadConfigs()
else:
	# Creating configs folder
	os.makedirs(getPath())
	log('Plugin: '+pName+' folder has been created')
