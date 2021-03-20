# Stores a pokemon based on dex number, moves, etc.
# Numbers are all based on known internal IDs

from enum import IntEnum, auto, Flag
import copy
import pypokedex as pkd
import codecs, re

WIN = False
# stores a full battle
class Replay():
    def __init__(self, fp, out):
        # throw away the garbage header data as well as other unwanted stuff
        self.preprocess(fp, out)
        fp.close()
        fp = codecs.open(out, 'r', "utf8")
        # the first important thing we want is the poke block
        # but first we need the team sizes because people are weird
        line = fp.readline()
        while (not line.startswith("|team")):
            line = fp.readline()
        
        # |teamsize|pX|int
        team1 = int(line.split('|')[3])
        line = fp.readline()
        team2 = int(line.split('|')[3])
        line = fp.readline()
        
        # just to make sure data isn't scuffed
        while (not line.startswith("|tier")):
            line = fp.readline()
        battle_format = line.split('|')[2]
        if (not battle_format.startswith("[Gen 8] OU")):
            print("Error, not a gen 8 OU replay: ", battle_format)
        
        # now to get the two teams
        line = fp.readline()
        # clearpoke is team preview signal
        # maybe we have a separate net to analyze the preview?
        while (not line.startswith("|clear")):
            line = fp.readline()
        pokemon = []
        poke_str = [[], []]
        temp = []
        
        # |poke|pX|<name>, <gender>|
        # we store the pokemon and the string to make it easier to index later
        for x in range(team1):
            line = fp.readline()
            nameList = line.split('|')[3].split(", ")
            if (len(nameList) == 1):
                temp.append(Pokemon(nameList[0], Gender.Genderless))
                poke_str[0].append(nameList[0].strip())
            else:
                if ("*" in nameList[0]): # 99% sure this is purely a case for urshifus alt form
                    nameList[0] = "Urshifu-Rapid-Strike"
                elif(nameList[0] == "Toxtricity"): # next error, PS does not care but the API does
                    nameList[0] = "Toxtricity-amped"
                temp.append(Pokemon(nameList[0], nameList[1]))
                poke_str[0].append(nameList[0].strip())
        pokemon.append(temp)
        
        temp = []

        for x in range(team2):
            line = fp.readline()
            nameList = line.split('|')[3].split(", ")
            if (len(nameList) == 1):
                temp.append(Pokemon(nameList[0], Gender.Genderless))
                poke_str[1].append(nameList[0].strip())
            else:                
                if ("*" in nameList[0]): # 99% sure this is purely a case for urshifus alt form
                    temp.append(Pokemon("Urshifu-Rapid-Strike", nameList[1]))
                    nameList[0] = "Urshifu"
                elif(nameList[0] == "Toxtricity"): # next error, PS does not care but the API does
                    temp.append(Pokemon("Toxtricity-amped", nameList[1]))
                else:
                    temp.append(Pokemon(nameList[0], nameList[1]))
                poke_str[1].append(nameList[0].strip())
        pokemon.append(temp)
        
        # somewhere here should be where we analyze the team preview
        # it can be as simple as taking their dex numbers and going off leads usage
        line = fp.readline()
        while (not line.startswith("|teampreview")):
            line = fp.readline()
        
        turns = []
        print("turn:", 0)
        turns.append(Turn(fp, pokemon, poke_str, None))
        
        line = fp.readline()
        i = 0
        while (not (WIN)):
            print("turn:", i + 1)
            turns.append(Turn(fp, pokemon, poke_str, turns[i]))
            i += 1
        
        fp.close()
        

    def preprocess(self, fp, out):
        line = fp.readline()
        everything = line.split("\\n")
        with open(out, "w") as fpw:
            everything.pop(0) # this is just metadata we don't need
            for x in everything:
                if (re.match("\|[cjl]\|.*" , x)): # delete leaves/joins/comments
                    pass
                else:
                    fpw.write(x + "\n")



####################################################################################
# Stores the state of one turn                                                     #
# a turn needs to know which moves are picked (either an actual move or switch)    #
# how much damage                                                                  #
# who moved first                                                                  #
# abilities that went off?                                                         #
# the turn id because why not                                                      #
# whether or not crit                                                              #
# weather/terrain                                                                  #
# maybe the super effective flag too?                                              #
####################################################################################
class Turn():
    # teampreview turn
    def __init__(self, fp, pokemon, poke_str, prev_turn):
        # first turns always start with a start instruction 
        # followed by switch instructions
        
        # vars:
        # p1Lead/p2Lead: int containing the index of the lead
        # first: who went first this turn
        # fields: the list in order of currently active fields
        if (prev_turn is None):
            self.p1Hazards = []
            self.p2Hazards = []
            self.p1Volatile = []
            self.p2Volatile = []
            self.p1Boosts = [0, 0, 0, 0, 0]
            self.p2Boosts = [0, 0, 0, 0, 0]
            self.p1Crit = False
            self.p2Crit = False
            self.isTurn0 = True
            self.insOrder = []
            self.p1Party = copy.deepcopy(pokemon[0])
            self.p2Party = copy.deepcopy(pokemon[1])
            
            line = fp.readline()
            while (not line.startswith("|start")): # first turn signal
                line = fp.readline()
            lead = fp.readline().split("|")
            
            # leads are determmined by speed?
            # idr if it's here or if you have to go off ability
            if (lead[2][1] == '1'):
                self.first = 1
                self.p1Lead = poke_str[0].index(lead[3].split(",")[0])
                lead = fp.readline().split("|")
                self.p2Lead = poke_str[1].index(lead[3].split(",")[0])
            else:
                self.first = 2
                self.p2Lead = poke_str[1].index(lead[3].split(",")[0])
                lead = fp.readline().split("|")
                self.p1Lead = poke_str[0].index(lead[3].split(",")[0])
            
            self.fields = [Field_List.NoField]
            
            line = fp.readline()
            # since turn 0 should only do field effects, we only check for them
            while (not line.startswith("|turn")):
                if (line.startswith("|-fieldstart")):
                    info = line.split("|")
                    field_str = info[2][6:].replace(" ", "")
                    self.fields.append(Field_List[field_str])
                    if (info[4][6] == '1'): # [4][6] is the player number
                        ability_str = info[3][15:].replace(" ", "")
                        pokemon[0][self.p1Lead].ability = Ability_List[ability_str]
                    else:
                        ability_str = info[3][15:].replace(" ", "")
                        pokemon[1][self.p2Lead].ability = Ability_List[ability_str]
                line = fp.readline()
        # this is for every actual turn
        else:
            # first get the previous turn leads and other stuff
            self.p1Lead = prev_turn.p1Lead
            self.p2Lead = prev_turn.p2Lead
            self.p1Hazards = prev_turn.p1Hazards 
            self.p2Hazards = prev_turn.p2Hazards 
            self.p1Volatile = prev_turn.p1Volatile
            self.p2Volatile = prev_turn.p2Volatile
            self.p1Boosts = prev_turn.p1Boosts
            self.p2Boosts = prev_turn.p2Boosts
            self.p1Crit = False
            self.p2Crit = False
            self.isTurn0 = False
            self.insOrder = []
            self.p1Party = copy.deepcopy(prev_turn.p1Party)
            self.p2Party = copy.deepcopy(prev_turn.p2Party)
            
            self.fields = copy.deepcopy(prev_turn.fields)
            
            line = fp.readline().strip()
            print(line)
            line = line.split("|")
            
            # loop to check every instruction in a turn
            # not too important but major actions do not have a prefix
            # minor actions have a "-" prefix
            # https://github.com/smogon/pokemon-showdown/blob/master/sim/SIM-PROTOCOL.md
            while (not line[1].startswith("turn")):
                # win con
                if (line[1].startswith("win")):
                    global WIN
                    WIN = True
                    return
                self.insOrder.append(line[1])
                # process a move
                # this involves adding the move if needed
                # and incrementing the pp value for that move
                # right now it ignores pressure, which should be fixed
                if (line[1].startswith("move")):
                    if (line[2][1] == '1'):
                        # this horrible mess changes an unknown move to a known one
                        if (not (line[3] in pokemon[0][self.p1Lead].Moves)):
                            pokemon[0][self.p1Lead].Moves[pokemon[0][self.p1Lead].Filled_Moves] = Move_List[line[3].replace(" ", "").replace("-", "")]
                            ind = pokemon[0][self.p1Lead].Filled_Moves
                        else: # if the move is there
                            ind = pokemon[0][self.p1Lead].Moves.index(Move_List[line[3].replace(" ", "")])
                        pokemon[0][self.p1Lead].PP[ind] += 1

                    else:
                        if (not (line[3] in pokemon[0][self.p2Lead].Moves)):
                            pokemon[0][self.p2Lead].Moves[pokemon[0][self.p2Lead].Filled_Moves] = Move_List[line[3].replace(" ", "")]
                            ind = pokemon[0][self.p2Lead].Filled_Moves
                        else: # if the move is there
                            ind = pokemon[0][self.p2Lead].Moves.index(Move_List[line[3].replace(" ", "")])
                        pokemon[0][self.p2Lead].PP[ind] += 1
                        
                # switch lead logic
                elif (line[1].startswith("switch")):
                    if (line[2][1] == '1'):
                        self.p1Lead = poke_str[0].index(line[3].split(",")[0])
                        self.p1Boosts = [0, 0, 0, 0, 0]
                    else:
                        self.p2Lead = poke_str[1].index(line[3].split(",")[0])
                        self.p2Boosts = [0, 0, 0, 0, 0]

                # handles a permanent change like megas
                # this is probably unused for OU
                elif (line[1].startswith("detailschange")):
                    pass
                
                # illusion reveal
                # effectively useless
                elif (line[1].startswith("replace")):
                    pass
                
                # double battle only
                elif (line[1].startswith("swap")):
                    pass
                    
                # the move could not be used
                # from para and disable
                elif (line[1].startswith("cant")):
                    pass

                # something died
                # I think this can be skipped
                elif (line[1].startswith("faint")):
                    pass

                # idk where this gets used, it's not block
                # can probably be skipped
                elif (line[1].startswith("-fail")):
                    pass

                # like fail but not
                # can probably be skipped
                elif (line[1].startswith("-block")):
                    pass

                # something fainted before the action
                # usually recoil death
                # can be skipped
                elif (line[1].startswith("-notarget")):
                    pass

                # your will-o-wisp didn't land again
                # can probably be skipped
                elif (line[1].startswith("-miss")):
                    pass

                # inflict damage
                elif (line[1].startswith("-damage")):
                    if (line[2][1] == '1'):
                        if ("fnt" in line[3]):
                            pokemon[0][self.p1Lead].HP = 0
                        else:
                            pokemon[0][self.p1Lead].HP = int(line[3].split("\\")[0])
                    else:
                        if ("fnt" in line[3]):
                            pokemon[0][self.p1Lead].HP = 0
                        else:
                            pokemon[1][self.p2Lead].HP = int(line[3].split("\\")[0])

                # inverse inflict damage
                elif (line[1].startswith("-heal")):
                    if (line[2][1] == '1'):
                        pokemon[0][self.p1Lead].HP = int(line[3].split("\\")[0])
                    else:
                        pokemon[1][self.p2Lead].HP = int(line[3].split("\\")[0])

                # ...what
                # maybe it's used for healing wish and clones?
                elif (line[1].startswith("-sethp")):
                    if (line[2][1] == '1'):
                        pokemon[0][self.p1Lead].HP = int(line[3].split("\\")[0])
                    else:
                        pokemon[1][self.p2Lead].HP = int(line[3].split("\\")[0])

                # inflict a status
                elif (line[1].startswith("-status")):
                    if (line[2][1] == '1'):
                        pokemon[0][self.p1Lead].Status = Status_List[line[3]]
                    else:
                        pokemon[1][self.p2Lead].Status = Status_List[line[3]]

                # basically just eating a berry?
                elif (line[1].startswith("-curestatus")):
                    if (line[2][1] == '1'):
                        pokemon[0][self.p1Lead].Status = Status_List.Non
                    else:
                        pokemon[1][self.p2Lead].Status = Status_List.Non

                # heal bell and aroma
                elif (line[1].startswith("-cureteam")):
                    if (line[2][1] == '1'):
                        for x in range(len(pokemon[0])):
                            pokemon[0][x].Status = Status_List.Non
                    else:
                        for x in range(len(pokemon[1])):
                            pokemon[1][x].Status = Status_List.Non

                # stat boosts
                elif (line[1].startswith("-boost")):
                    stat = Stat_List[line[3] + 'S']
                    if (line[2][1] == '1'):
                        self.p1Boosts[stat] = int(line[4])
                    else:
                        self.p2Boosts[stat] = int(line[4])

                # inverse stat boosts
                elif (line[1].startswith("-unboost")):
                    stat = Stat_List[line[3] + 'S']
                    if (line[2][1] == '1'):
                        self.p1Boosts[stat] = int(line[4])
                    else:
                        self.p2Boosts[stat] = int(line[4])

                # trade stat boosts between two pokemon
                # pretty sure this doesn't matter
                elif (line[1].startswith("-swapboost")):
                    pass

                # topsy-turvy
                elif (line[1].startswith("-invertboost")):
                    if (line[2][1] == '1'):
                        for x in range(pokemon[0]):
                            self.p1Boosts[x] *= -1
                    else:
                        for x in range(pokemon[1]):
                            self.p2Boosts[x] *= -1

                # clear smog
                elif (line[1].startswith("-clearboost")):
                    if (line[2][1] == '1'):
                        for x in range(pokemon[0]):
                            self.p1Boosts[x] = 0
                    else:
                        for x in range(pokemon[1]):
                            self.p2Boosts[x] = 0

                # haze clears the whole field
                elif (line[1].startswith("-clearallboost")):
                    self.p1Boosts[x] = [0, 0, 0, 0, 0]
                    self.p2Boosts[x] = [0, 0, 0, 0, 0]

                # spec thief logic, unused I think
                elif (line[1].startswith("-clearpositiveboost")):
                    if (line[2][1] == '1'):
                        for x in range(5):
                            if (self.p1Boosts[x] > 0):
                                self.p1Boosts[x] = 0
                    else:
                        for x in range(5):
                            if (self.p1Boosts[x] > 0):
                                self.p1Boosts[x] = 0

                # unused in gen 8?
                elif (line[1].startswith("-clearnegativeboost")):
                    if (line[2][1] == '1'):
                        for x in range(5):
                            if (self.p1Boosts[x] < 0):
                                self.p1Boosts[x] = 0
                    else:
                        for x in range(5):
                            if (self.p1Boosts[x] < 0):
                                self.p1Boosts[x] = 0

                # unused in gen 8?
                elif (line[1].startswith("-copyboost")):
                    pass

                # rain and stuff
                elif (line[1].startswith("-weather")):
                    self.fields.append(Field_List[line[2][5:].replace(" ", "")])

                # terrain/room start
                elif (line[1].startswith("-fieldstart")):
                    self.fields.append(Field_List[line[2][5:].replace(" ", "")])

                # terrain/room end
                elif (line[1].startswith("-fieldend")):
                    self.fields.remove(Field_List[line[2][5:].replace(" ", "")])

                # this is where stealth rock and other one side events happen
                elif (line[1].startswith("-sidestart")):
                    if (line[2][1] == '1'):
                        self.p1Hazards.append(line[3].replace(" ", ""))
                    else:
                        self.p2Hazards.append(line[3].replace(" ", ""))

                # inverse side start, idk where this will appear
                # besides defog
                elif (line[1].startswith("-sideend")):
                    if (line[2][1] == '1'):
                        self.p1Hazards.remove(line[3].replace(" ", ""))
                    else:
                        self.p2Hazards.remove(line[3].replace(" ", ""))

                # volatile status (confusion, taunt, sub)
                elif (line[1].startswith("-start")):
                    if (line[2][1] == '1'):
                        self.p1Volatile.append(line[3].replace(" ", ""))
                    else:
                        self.p2Volatile.append(line[3].replace(" ", ""))

                # inverse volatile status (confusion, taunt, sub)
                elif (line[1].startswith("-end")):
                    if (line[2][1] == '1'):
                        self.p1Volatile.remove(line[3].replace(" ", ""))
                    else:
                        self.p2Volatile.remove(line[3].replace(" ", ""))

                # it always mattered
                elif (line[1].startswith("-crit")):
                    if (line[2][1] == '1'):
                        self.p1Crit = True
                    else:
                        self.p2Crit = True

                # yes
                # idt this matters since the numbers would be bigger anyways
                elif (line[1].startswith("-supereffective")):
                    pass

                # no
                # idt this matters since the numbers would be smaller anyways
                elif (line[1].startswith("-resisted")):
                    pass

                # NO
                # idt this matters since the numbers would be 0 anyways
                elif (line[1].startswith("-immune")):
                    pass

                # leftovers/life orb reveal
                elif (line[1].startswith("-item")):
                    if (line[2][1] == '1'):
                        pokemon[0][self.p1Lead].item = line[3].replace(" ", "")
                    else:
                        pokemon[1][self.p2Lead].item = line[3].replace(" ", "")

                # knock off
                elif (line[1].startswith("-enditem")):
                    if (line[2][1] == '1'):
                        pokemon[0][self.p1Lead].item = "None"
                    else:
                        pokemon[1][self.p2Lead].item = "None"

                # set the ability on a pokemon
                # and maybe also handle intimidate and stuff
                elif (line[1].startswith("-ability")):
                    if (line[2][1] == '1'):
                        pokemon[0][self.p1Lead].Ability = Ability_List[line[3].replace(" ", "")]
                    else:
                        pokemon[1][self.p2Lead].Ability = Ability_List[line[3].replace(" ", "")]

                # suppressed by gastro acid
                # idk how to even approach this
                elif (line[1].startswith("-endability")):
                    pass

                # ditto is cool
                # idk how to approach this either
                elif (line[1].startswith("-transform")):
                    pass

                # unused in gen 8
                elif (line[1].startswith("-primal")):
                    pass

                # unused in gen 8?
                elif (line[1].startswith("-burst")):
                    pass

                # unused in gen 8?
                elif (line[1].startswith("-zpower")):
                    pass

                # unused in gen 8?
                elif (line[1].startswith("-zbroken")):
                    pass

                # basically useless info?
                elif (line[1].startswith("-activate")):
                    pass

                # basically useless info?
                elif (line[1].startswith("-hint")):
                    pass

                # basically useless info?
                elif (line[1].startswith("-center")):
                    pass

                # other messages for stuff like rules, useless
                elif (line[1].startswith("-message")):
                    pass

                # useless in singles
                elif (line[1].startswith("-combine")):
                    pass

                # useless in singles
                elif (line[1].startswith("-waiting")):
                    pass

                # charge moves, I hope this is useless
                elif (line[1].startswith("-prepare")):
                    pass

                # charge moves, I hope this is useless
                elif (line[1].startswith("-mustrecharge")):
                    pass

                # splash
                elif (line[1].startswith("-nothing")):
                    pass

                # the definition for this is that it updates turn timers
                # idk if we want to worry about that
                elif (line[1].startswith("upkeep")):
                    pass

                # cloyster go brrr
                elif (line[1].startswith("-hitcount")):
                    pass

                # d-bond
                elif (line[1].startswith("-singlemove")):
                    pass

                # protect, focus punch, roost
                elif (line[1].startswith("-singleturn")):
                    pass

                # timestamp
                elif (line[1].startswith("t:")):
                    pass

                # idek, blanks appear
                elif (line[1].startswith("")):
                    pass

                else:
                    print("Error, unknown instruction:", line[1])
                    exit()

                    
                line = fp.readline().strip()
                print(line)
                line = line.split("|")
            
            return


    def predictSpeed(self): # if this returns true, speed is currently "accurate"
        #return self.p1Party[self.p1Lead].
        return True
        
    def makeVector(self):
        theMonster = [] # this should contain the party and anything else that might be useful
        output = [] # this should contain the moves and switches people clicked
        #if (self.isTurn0):
            #for x in self.p1Party:
                
            #theMonster.append(self.first)
        # else:

    # going to try to follow the PS turn style
    def __str__(self):
        if (self.isTurn0):
            string = "Start\nP{} sends out: ".format(self.first)
            # this logic probably matters
            if (self.first == 1):
                string += self.p1Lead + "\nP2 sends out: " + self.p2Lead
            else:
                string += self.p2Lead + "\nP1 sends out: " + self.p1Lead

            if (len(self.fields) > 1):
                for x in self.fields[1:]:
                    string += "\n" + str(x) + "\n" # this part does not print properly but it's too much work
            string += "End of turn 0"
        else:
            pass

        return string


####################################################################################
# defines a single pokemon                                                         #
# data stored includes:                                                            #
# the pokemon itself as a pypokedex object: for accessing the dex number           #
# known and unknown moves as well as used PP: traditionally this affects decisions #
# on what switch ins to make, and unknown moves are powerful                       #
# ability,gender and item: influence what sets are being run and decisions         #
####################################################################################
class Pokemon():
    # default values, idek if this is needed
    # def __init__(self):
    #     self.Pkmn = pkd.get(name='Porygon') # idk if this is necessary
    #     # Name = 'Porygon'
    #     self.Moves = [Move_List.Unknown, Move_List.Unknown, Move_List.Unknown, Move_List.Unknown]
    #     self.Filled_Moves = 0
    #     self.PP = [0, 0, 0, 0] # this might have to be the number used and not a count down
    #     self.Ability = Ability_List.Unknown
    #     self.Item = "" # this needs to be enumerated somehow; PS and PKHeX lack sane enums
    #     self.Gender = Gender.Genderless
    #     self.Level = 100 # this should be changed at some point
    #     self.Speed = self.calcSpeed()
    #     self.HP = 100
    #     self.Boosts = [0, 0, 0, 0, 0]
    #     self.Status = Status_List.non
        
    
    # initalizer for known pokemon
    def __init__(self, name="Porygon", gender="Genderless"):
        self.Pkmn = pkd.get(name=name)
        self.Moves = [Move_List.Unknown, Move_List.Unknown, Move_List.Unknown, Move_List.Unknown]
        self.Filled_Moves = 0
        self.PP = [0, 0, 0, 0]
        self.Ability = Ability_List.Unknown
        self.Item = ""
        self.Gender = gender
        self.Level = 100 # this should be changed at some point
        self.Speed = self.calcSpeed()
        self.HP = 100
        self.Status = Status_List.non
        
    def calcSpeed(self): # this will assume neutral speed 0 ev investment
        return ((2 * self.Pkmn.base_stats[5] + 31) * self.Level) / 100 + 5
        
    def GetVector(self):
        stats = self.Pkmn.base_stats
        return [self.Pkmn.dex, # dex number
        self.stats[0], self.stats[1], self.stats[2], # HP,  Atk, Def
        self.stats[3], self.stats[4], self.stats[5], # SpA, SpD, Spe
        self.Moves[0], self.PP[0],                   # move 1
        self.Moves[1], self.PP[1],                   # move 2
        self.Moves[2], self.PP[2],                   # move 3
        self.Moves[3], self.PP[3],                   # move 4
        self.Ability] # anything else should be appended here

    # Tries to follow the showdown format because why not, some things are changed for readability
    def __str__(self):
        string = self.name
        if (self.Item):
            string += "@ " + self.Item
        string += "\nAbility: " + self.Ability
        # string += "EVs:" # this would not work unless we galaxy brain predict them somehow
        # string += Nature + " Nature" # above
        
        if (self.Moves[0] == self.Move.Unknown):
            string += "No known moves"
        else:
            string += "- " + self.Moves[0].name + "(" + self.PP[0] + ")\n" + \
                      "- " + self.Moves[1].name + "(" + self.PP[1] + ")\n" + \
                      "- " + self.Moves[2].name + "(" + self.PP[2] + ")\n" + \
                      "- " + self.Moves[3].name + "(" + self.PP[3] + ")\n"

# Gender is something that PS keeps track of so we might as well have it
class Gender(IntEnum):
    G = 0
    M = 1
    F = 2

# Volatile status are things that can get cleared over time or on switch
class Volatile_List(IntEnum):
    Bind = auto()
    Block = auto()
    Confusion = auto()
    Substitute = auto()
    

class Stat_List(IntEnum):
    atkS = 0
    defS = 1
    spaS = 2
    spdS = 3
    speS = 4
####################################################################################
# Move and ability lists derived from here because they are sorted                 #
# https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/Game/Enums/                #
# this order was derived from data mining the video games and has not changed      #
# since gen 1                                                                      #
####################################################################################
class Move_List(IntEnum):
    Unknown = auto() # the only change because None is a keyword
    Pound = auto()
    KarateChop = auto()
    DoubleSlap = auto()
    CometPunch = auto()
    MegaPunch = auto()
    PayDay = auto()
    FirePunch = auto()
    IcePunch = auto()
    ThunderPunch = auto()
    Scratch = auto()
    ViseGrip = auto()
    Guillotine = auto()
    RazorWind = auto()
    SwordsDance = auto()
    Cut = auto()
    Gust = auto()
    WingAttack = auto()
    Whirlwind = auto()
    Fly = auto()
    Bind = auto()
    Slam = auto()
    VineWhip = auto()
    Stomp = auto()
    DoubleKick = auto()
    MegaKick = auto()
    JumpKick = auto()
    RollingKick = auto()
    SandAttack = auto()
    Headbutt = auto()
    HornAttack = auto()
    FuryAttack = auto()
    HornDrill = auto()
    Tackle = auto()
    BodySlam = auto()
    Wrap = auto()
    TakeDown = auto()
    Thrash = auto()
    DoubleEdge = auto()
    TailWhip = auto()
    PoisonSting = auto()
    Twineedle = auto()
    PinMissile = auto()
    Leer = auto()
    Bite = auto()
    Growl = auto()
    Roar = auto()
    Sing = auto()
    Supersonic = auto()
    SonicBoom = auto()
    Disable = auto()
    Acid = auto()
    Ember = auto()
    Flamethrower = auto()
    Mist = auto()
    WaterGun = auto()
    HydroPump = auto()
    Surf = auto()
    IceBeam = auto()
    Blizzard = auto()
    Psybeam = auto()
    BubbleBeam = auto()
    AuroraBeam = auto()
    HyperBeam = auto()
    Peck = auto()
    DrillPeck = auto()
    Submission = auto()
    LowKick = auto()
    Counter = auto()
    SeismicToss = auto()
    Strength = auto()
    Absorb = auto()
    MegaDrain = auto()
    LeechSeed = auto()
    Growth = auto()
    RazorLeaf = auto()
    SolarBeam = auto()
    PoisonPowder = auto()
    StunSpore = auto()
    SleepPowder = auto()
    PetalDance = auto()
    StringShot = auto()
    DragonRage = auto()
    FireSpin = auto()
    ThunderShock = auto()
    Thunderbolt = auto()
    ThunderWave = auto()
    Thunder = auto()
    RockThrow = auto()
    Earthquake = auto()
    Fissure = auto()
    Dig = auto()
    Toxic = auto()
    Confusion = auto()
    Psychic = auto()
    Hypnosis = auto()
    Meditate = auto()
    Agility = auto()
    QuickAttack = auto()
    Rage = auto()
    Teleport = auto()
    NightShade = auto()
    Mimic = auto()
    Screech = auto()
    DoubleTeam = auto()
    Recover = auto()
    Harden = auto()
    Minimize = auto()
    Smokescreen = auto()
    ConfuseRay = auto()
    Withdraw = auto()
    DefenseCurl = auto()
    Barrier = auto()
    LightScreen = auto()
    Haze = auto()
    Reflect = auto()
    FocusEnergy = auto()
    Bide = auto()
    Metronome = auto()
    MirrorMove = auto()
    SelfDestruct = auto()
    EggBomb = auto()
    Lick = auto()
    Smog = auto()
    Sludge = auto()
    BoneClub = auto()
    FireBlast = auto()
    Waterfall = auto()
    Clamp = auto()
    Swift = auto()
    SkullBash = auto()
    SpikeCannon = auto()
    Constrict = auto()
    Amnesia = auto()
    Kinesis = auto()
    SoftBoiled = auto()
    HighJumpKick = auto()
    Glare = auto()
    DreamEater = auto()
    PoisonGas = auto()
    Barrage = auto()
    LeechLife = auto()
    LovelyKiss = auto()
    SkyAttack = auto()
    Transform = auto()
    Bubble = auto()
    DizzyPunch = auto()
    Spore = auto()
    Flash = auto()
    Psywave = auto()
    Splash = auto()
    AcidArmor = auto()
    Crabhammer = auto()
    Explosion = auto()
    FurySwipes = auto()
    Bonemerang = auto()
    Rest = auto()
    RockSlide = auto()
    HyperFang = auto()
    Sharpen = auto()
    Conversion = auto()
    TriAttack = auto()
    SuperFang = auto()
    Slash = auto()
    Substitute = auto()
    Struggle = auto()
    Sketch = auto()
    TripleKick = auto()
    Thief = auto()
    SpiderWeb = auto()
    MindReader = auto()
    Nightmare = auto()
    FlameWheel = auto()
    Snore = auto()
    Curse = auto()
    Flail = auto()
    Conversion2 = auto()
    Aeroblast = auto()
    CottonSpore = auto()
    Reversal = auto()
    Spite = auto()
    PowderSnow = auto()
    Protect = auto()
    MachPunch = auto()
    ScaryFace = auto()
    FeintAttack = auto()
    SweetKiss = auto()
    BellyDrum = auto()
    SludgeBomb = auto()
    MudSlap = auto()
    Octazooka = auto()
    Spikes = auto()
    ZapCannon = auto()
    Foresight = auto()
    DestinyBond = auto()
    PerishSong = auto()
    IcyWind = auto()
    Detect = auto()
    BoneRush = auto()
    LockOn = auto()
    Outrage = auto()
    Sandstorm = auto()
    GigaDrain = auto()
    Endure = auto()
    Charm = auto()
    Rollout = auto()
    FalseSwipe = auto()
    Swagger = auto()
    MilkDrink = auto()
    Spark = auto()
    FuryCutter = auto()
    SteelWing = auto()
    MeanLook = auto()
    Attract = auto()
    SleepTalk = auto()
    HealBell = auto()
    Return = auto()
    Present = auto()
    Frustration = auto()
    Safeguard = auto()
    PainSplit = auto()
    SacredFire = auto()
    Magnitude = auto()
    DynamicPunch = auto()
    Megahorn = auto()
    DragonBreath = auto()
    BatonPass = auto()
    Encore = auto()
    Pursuit = auto()
    RapidSpin = auto()
    SweetScent = auto()
    IronTail = auto()
    MetalClaw = auto()
    VitalThrow = auto()
    MorningSun = auto()
    Synthesis = auto()
    Moonlight = auto()
    HiddenPower = auto()
    CrossChop = auto()
    Twister = auto()
    RainDance = auto()
    SunnyDay = auto()
    Crunch = auto()
    MirrorCoat = auto()
    PsychUp = auto()
    ExtremeSpeed = auto()
    AncientPower = auto()
    ShadowBall = auto()
    FutureSight = auto()
    RockSmash = auto()
    Whirlpool = auto()
    BeatUp = auto()
    FakeOut = auto()
    Uproar = auto()
    Stockpile = auto()
    SpitUp = auto()
    Swallow = auto()
    HeatWave = auto()
    Hail = auto()
    Torment = auto()
    Flatter = auto()
    WillOWisp = auto()
    Memento = auto()
    Facade = auto()
    FocusPunch = auto()
    SmellingSalts = auto()
    FollowMe = auto()
    NaturePower = auto()
    Charge = auto()
    Taunt = auto()
    HelpingHand = auto()
    Trick = auto()
    RolePlay = auto()
    Wish = auto()
    Assist = auto()
    Ingrain = auto()
    Superpower = auto()
    MagicCoat = auto()
    Recycle = auto()
    Revenge = auto()
    BrickBreak = auto()
    Yawn = auto()
    KnockOff = auto()
    Endeavor = auto()
    Eruption = auto()
    SkillSwap = auto()
    Imprison = auto()
    Refresh = auto()
    Grudge = auto()
    Snatch = auto()
    SecretPower = auto()
    Dive = auto()
    ArmThrust = auto()
    Camouflage = auto()
    TailGlow = auto()
    LusterPurge = auto()
    MistBall = auto()
    FeatherDance = auto()
    TeeterDance = auto()
    BlazeKick = auto()
    MudSport = auto()
    IceBall = auto()
    NeedleArm = auto()
    SlackOff = auto()
    HyperVoice = auto()
    PoisonFang = auto()
    CrushClaw = auto()
    BlastBurn = auto()
    HydroCannon = auto()
    MeteorMash = auto()
    Astonish = auto()
    WeatherBall = auto()
    Aromatherapy = auto()
    FakeTears = auto()
    AirCutter = auto()
    Overheat = auto()
    OdorSleuth = auto()
    RockTomb = auto()
    SilverWind = auto()
    MetalSound = auto()
    GrassWhistle = auto()
    Tickle = auto()
    CosmicPower = auto()
    WaterSpout = auto()
    SignalBeam = auto()
    ShadowPunch = auto()
    Extrasensory = auto()
    SkyUppercut = auto()
    SandTomb = auto()
    SheerCold = auto()
    MuddyWater = auto()
    BulletSeed = auto()
    AerialAce = auto()
    IcicleSpear = auto()
    IronDefense = auto()
    Block = auto()
    Howl = auto()
    DragonClaw = auto()
    FrenzyPlant = auto()
    BulkUp = auto()
    Bounce = auto()
    MudShot = auto()
    PoisonTail = auto()
    Covet = auto()
    VoltTackle = auto()
    MagicalLeaf = auto()
    WaterSport = auto()
    CalmMind = auto()
    LeafBlade = auto()
    DragonDance = auto()
    RockBlast = auto()
    ShockWave = auto()
    WaterPulse = auto()
    DoomDesire = auto()
    PsychoBoost = auto()
    Roost = auto()
    Gravity = auto()
    MiracleEye = auto()
    WakeUpSlap = auto()
    HammerArm = auto()
    GyroBall = auto()
    HealingWish = auto()
    Brine = auto()
    NaturalGift = auto()
    Feint = auto()
    Pluck = auto()
    Tailwind = auto()
    Acupressure = auto()
    MetalBurst = auto()
    Uturn = auto()
    CloseCombat = auto()
    Payback = auto()
    Assurance = auto()
    Embargo = auto()
    Fling = auto()
    PsychoShift = auto()
    TrumpCard = auto()
    HealBlock = auto()
    WringOut = auto()
    PowerTrick = auto()
    GastroAcid = auto()
    LuckyChant = auto()
    MeFirst = auto()
    Copycat = auto()
    PowerSwap = auto()
    GuardSwap = auto()
    Punishment = auto()
    LastResort = auto()
    WorrySeed = auto()
    SuckerPunch = auto()
    ToxicSpikes = auto()
    HeartSwap = auto()
    AquaRing = auto()
    MagnetRise = auto()
    FlareBlitz = auto()
    ForcePalm = auto()
    AuraSphere = auto()
    RockPolish = auto()
    PoisonJab = auto()
    DarkPulse = auto()
    NightSlash = auto()
    AquaTail = auto()
    SeedBomb = auto()
    AirSlash = auto()
    XScissor = auto()
    BugBuzz = auto()
    DragonPulse = auto()
    DragonRush = auto()
    PowerGem = auto()
    DrainPunch = auto()
    VacuumWave = auto()
    FocusBlast = auto()
    EnergyBall = auto()
    BraveBird = auto()
    EarthPower = auto()
    Switcheroo = auto()
    GigaImpact = auto()
    NastyPlot = auto()
    BulletPunch = auto()
    Avalanche = auto()
    IceShard = auto()
    ShadowClaw = auto()
    ThunderFang = auto()
    IceFang = auto()
    FireFang = auto()
    ShadowSneak = auto()
    MudBomb = auto()
    PsychoCut = auto()
    ZenHeadbutt = auto()
    MirrorShot = auto()
    FlashCannon = auto()
    RockClimb = auto()
    Defog = auto()
    TrickRoom = auto()
    DracoMeteor = auto()
    Discharge = auto()
    LavaPlume = auto()
    LeafStorm = auto()
    PowerWhip = auto()
    RockWrecker = auto()
    CrossPoison = auto()
    GunkShot = auto()
    IronHead = auto()
    MagnetBomb = auto()
    StoneEdge = auto()
    Captivate = auto()
    StealthRock = auto()
    GrassKnot = auto()
    Chatter = auto()
    Judgment = auto()
    BugBite = auto()
    ChargeBeam = auto()
    WoodHammer = auto()
    AquaJet = auto()
    AttackOrder = auto()
    DefendOrder = auto()
    HealOrder = auto()
    HeadSmash = auto()
    DoubleHit = auto()
    RoarofTime = auto()
    SpacialRend = auto()
    LunarDance = auto()
    CrushGrip = auto()
    MagmaStorm = auto()
    DarkVoid = auto()
    SeedFlare = auto()
    OminousWind = auto()
    ShadowForce = auto()
    HoneClaws = auto()
    WideGuard = auto()
    GuardSplit = auto()
    PowerSplit = auto()
    WonderRoom = auto()
    Psyshock = auto()
    Venoshock = auto()
    Autotomize = auto()
    RagePowder = auto()
    Telekinesis = auto()
    MagicRoom = auto()
    SmackDown = auto()
    StormThrow = auto()
    FlameBurst = auto()
    SludgeWave = auto()
    QuiverDance = auto()
    HeavySlam = auto()
    Synchronoise = auto()
    ElectroBall = auto()
    Soak = auto()
    FlameCharge = auto()
    Coil = auto()
    LowSweep = auto()
    AcidSpray = auto()
    FoulPlay = auto()
    SimpleBeam = auto()
    Entrainment = auto()
    AfterYou = auto()
    Round = auto()
    EchoedVoice = auto()
    ChipAway = auto()
    ClearSmog = auto()
    StoredPower = auto()
    QuickGuard = auto()
    AllySwitch = auto()
    Scald = auto()
    ShellSmash = auto()
    HealPulse = auto()
    Hex = auto()
    SkyDrop = auto()
    ShiftGear = auto()
    CircleThrow = auto()
    Incinerate = auto()
    Quash = auto()
    Acrobatics = auto()
    ReflectType = auto()
    Retaliate = auto()
    FinalGambit = auto()
    Bestow = auto()
    Inferno = auto()
    WaterPledge = auto()
    FirePledge = auto()
    GrassPledge = auto()
    VoltSwitch = auto()
    StruggleBug = auto()
    Bulldoze = auto()
    FrostBreath = auto()
    DragonTail = auto()
    WorkUp = auto()
    Electroweb = auto()
    WildCharge = auto()
    DrillRun = auto()
    DualChop = auto()
    HeartStamp = auto()
    HornLeech = auto()
    SacredSword = auto()
    RazorShell = auto()
    HeatCrash = auto()
    LeafTornado = auto()
    Steamroller = auto()
    CottonGuard = auto()
    NightDaze = auto()
    Psystrike = auto()
    TailSlap = auto()
    Hurricane = auto()
    HeadCharge = auto()
    GearGrind = auto()
    SearingShot = auto()
    TechnoBlast = auto()
    RelicSong = auto()
    SecretSword = auto()
    Glaciate = auto()
    BoltStrike = auto()
    BlueFlare = auto()
    FieryDance = auto()
    FreezeShock = auto()
    IceBurn = auto()
    Snarl = auto()
    IcicleCrash = auto()
    Vcreate = auto()
    FusionFlare = auto()
    FusionBolt = auto()
    FlyingPress = auto()
    MatBlock = auto()
    Belch = auto()
    Rototiller = auto()
    StickyWeb = auto()
    FellStinger = auto()
    PhantomForce = auto()
    TrickorTreat = auto()
    NobleRoar = auto()
    IonDeluge = auto()
    ParabolicCharge = auto()
    ForestsCurse = auto()
    PetalBlizzard = auto()
    FreezeDry = auto()
    DisarmingVoice = auto()
    PartingShot = auto()
    TopsyTurvy = auto()
    DrainingKiss = auto()
    CraftyShield = auto()
    FlowerShield = auto()
    GrassyTerrain = auto()
    MistyTerrain = auto()
    Electrify = auto()
    PlayRough = auto()
    FairyWind = auto()
    Moonblast = auto()
    Boomburst = auto()
    FairyLock = auto()
    KingsShield = auto()
    PlayNice = auto()
    Confide = auto()
    DiamondStorm = auto()
    SteamEruption = auto()
    HyperspaceHole = auto()
    WaterShuriken = auto()
    MysticalFire = auto()
    SpikyShield = auto()
    AromaticMist = auto()
    EerieImpulse = auto()
    VenomDrench = auto()
    Powder = auto()
    Geomancy = auto()
    MagneticFlux = auto()
    HappyHour = auto()
    ElectricTerrain = auto()
    DazzlingGleam = auto()
    Celebrate = auto()
    HoldHands = auto()
    BabyDollEyes = auto()
    Nuzzle = auto()
    HoldBack = auto()
    Infestation = auto()
    PowerUpPunch = auto()
    OblivionWing = auto()
    ThousandArrows = auto()
    ThousandWaves = auto()
    LandsWrath = auto()
    LightofRuin = auto()
    OriginPulse = auto()
    PrecipiceBlades = auto()
    DragonAscent = auto()
    HyperspaceFury = auto()
    BreakneckBlitzP = auto()
    BreakneckBlitzS = auto()
    AllOutPummelingP = auto()
    AllOutPummelingS = auto()
    SupersonicSkystrikeP = auto()
    SupersonicSkystrikeS = auto()
    AcidDownpourP = auto()
    AcidDownpourS = auto()
    TectonicRageP = auto()
    TectonicRageS = auto()
    ContinentalCrushP = auto()
    ContinentalCrushS = auto()
    SavageSpinOutP = auto()
    SavageSpinOutS = auto()
    NeverEndingNightmareP = auto()
    NeverEndingNightmareS = auto()
    CorkscrewCrashP = auto()
    CorkscrewCrashS = auto()
    InfernoOverdriveP = auto()
    InfernoOverdriveS = auto()
    HydroVortexP = auto()
    HydroVortexS = auto()
    BloomDoomP = auto()
    BloomDoomS = auto()
    GigavoltHavocP = auto()
    GigavoltHavocS = auto()
    ShatteredPsycheP = auto()
    ShatteredPsycheS = auto()
    SubzeroSlammerP = auto()
    SubzeroSlammerS = auto()
    DevastatingDrakeP = auto()
    DevastatingDrakeS = auto()
    BlackHoleEclipseP = auto()
    BlackHoleEclipseS = auto()
    TwinkleTackleP = auto()
    TwinkleTackleS = auto()
    Catastropika = auto()
    ShoreUp = auto()
    FirstImpression = auto()
    BanefulBunker = auto()
    SpiritShackle = auto()
    DarkestLariat = auto()
    SparklingAria = auto()
    IceHammer = auto()
    FloralHealing = auto()
    HighHorsepower = auto()
    StrengthSap = auto()
    SolarBlade = auto()
    Leafage = auto()
    Spotlight = auto()
    ToxicThread = auto()
    LaserFocus = auto()
    GearUp = auto()
    ThroatChop = auto()
    PollenPuff = auto()
    AnchorShot = auto()
    PsychicTerrain = auto()
    Lunge = auto()
    FireLash = auto()
    PowerTrip = auto()
    BurnUp = auto()
    SpeedSwap = auto()
    SmartStrike = auto()
    Purify = auto()
    RevelationDance = auto()
    CoreEnforcer = auto()
    TropKick = auto()
    Instruct = auto()
    BeakBlast = auto()
    ClangingScales = auto()
    DragonHammer = auto()
    BrutalSwing = auto()
    AuroraVeil = auto()
    SinisterArrowRaid = auto()
    MaliciousMoonsault = auto()
    OceanicOperetta = auto()
    GuardianofAlola = auto()
    SoulStealing7StarStrike = auto()
    StokedSparksurfer = auto()
    PulverizingPancake = auto()
    ExtremeEvoboost = auto()
    GenesisSupernova = auto()
    ShellTrap = auto()
    FleurCannon = auto()
    PsychicFangs = auto()
    StompingTantrum = auto()
    ShadowBone = auto()
    Accelerock = auto()
    Liquidation = auto()
    PrismaticLaser = auto()
    SpectralThief = auto()
    SunsteelStrike = auto()
    MoongeistBeam = auto()
    TearfulLook = auto()
    ZingZap = auto()
    NaturesMadness = auto()
    MultiAttack = auto()
    TenMVoltThunderbolt = auto()
    MindBlown = auto()
    PlasmaFists = auto()
    PhotonGeyser = auto()
    LightThatBurnstheSky = auto()
    SearingSunrazeSmash = auto()
    MenacingMoonrazeMaelstrom = auto()
    LetsSnuggleForever = auto()
    SplinteredStormshards = auto()
    ClangorousSoulblaze = auto()
    ZippyZap = auto()
    SplishySplash = auto()
    FloatyFall = auto()
    PikaPapow = auto()
    BouncyBubble = auto()
    BuzzyBuzz = auto()
    SizzlySlide = auto()
    GlitzyGlow = auto()
    BaddyBad = auto()
    SappySeed = auto()
    FreezyFrost = auto()
    SparklySwirl = auto()
    VeeveeVolley = auto()
    DoubleIronBash = auto()
    MaxGuard = auto()
    DynamaxCannon = auto()
    SnipeShot = auto()
    JawLock = auto()
    StuffCheeks = auto()
    NoRetreat = auto()
    TarShot = auto()
    MagicPowder = auto()
    DragonDarts = auto()
    Teatime = auto()
    Octolock = auto()
    BoltBeak = auto()
    FishiousRend = auto()
    CourtChange = auto()
    MaxFlare = auto()
    MaxFlutterby = auto()
    MaxLightning = auto()
    MaxStrike = auto()
    MaxKnuckle = auto()
    MaxPhantasm = auto()
    MaxHailstorm = auto()
    MaxOoze = auto()
    MaxGeyser = auto()
    MaxAirstream = auto()
    MaxStarfall = auto()
    MaxWyrmwind = auto()
    MaxMindstorm = auto()
    MaxRockfall = auto()
    MaxQuake = auto()
    MaxDarkness = auto()
    MaxOvergrowth = auto()
    MaxSteelspike = auto()
    ClangorousSoul = auto()
    BodyPress = auto()
    Decorate = auto()
    DrumBeating = auto()
    SnapTrap = auto()
    PyroBall = auto()
    BehemothBlade = auto()
    BehemothBash = auto()
    AuraWheel = auto()
    BreakingSwipe = auto()
    BranchPoke = auto()
    Overdrive = auto()
    AppleAcid = auto()
    GravApple = auto()
    SpiritBreak = auto()
    StrangeSteam = auto()
    LifeDew = auto()
    Obstruct = auto()
    FalseSurrender = auto()
    MeteorAssault = auto()
    Eternabeam = auto()
    SteelBeam = auto()
    ExpandingForce = auto()
    SteelRoller = auto()
    ScaleShot = auto()
    MeteorBeam = auto()
    ShellSideArm = auto()
    MistyExplosion = auto()
    GrassyGlide = auto()
    RisingVoltage = auto()
    TerrainPulse = auto()
    SkitterSmack = auto()
    BurningJealousy = auto()
    LashOut = auto()
    Poltergeist = auto()
    CorrosiveGas = auto()
    Coaching = auto()
    FlipTurn = auto()
    TripleAxel = auto()
    DualWingbeat = auto()
    ScorchingSands = auto()
    JungleHealing = auto()
    WickedBlow = auto()
    SurgingStrikes = auto()
    ThunderCage = auto()
    DragonEnergy = auto()
    FreezingGlare = auto()
    FieryWrath = auto()
    ThunderousKick = auto()
    GlacialLance = auto()
    AstralBarrage = auto()
    EerieSpell = auto()

# status effects, they get cured by lum berry for definition?
class Status_List(IntEnum):
    non = auto()
    brn = auto()
    par = auto()
    frz = auto()
    psn = auto()
    tox = auto()
    slp = auto()
    
# Field effects are things that affect both sides
# This is the first and second block in the field of the damage calc
# Missing ones cannot exist in OU
class Field_List(IntEnum):
    NoField = auto()
    ElectricTerrain = auto()
    GrassyTerrain = auto()
    MistyTerrain = auto()
    PsychicTerrain = auto()
    Sun = auto()
    Rain = auto()
    Sand = auto()
    Hail = auto()
    TrickRoom = auto()
    WonderRoom = auto()
    
# Side effects are things that are only found on one side
# This is the third block on the damage calc
# Missing ones cannot be in OU
class Hazards_List(Flag):
    Stealth_Rock = auto()
    Spikes = auto()
    Spikes2 = auto()
    Spikes3 = auto()
    Reflect = auto()
    LightScreen = auto()
    Protect = auto()
    LeechSeed = auto()
    Foresight = auto()
    Tailwind = auto()
    AuroraVeil = auto()
    Battery = auto()

# see Move dscription
class Ability_List(IntEnum):
    Unknown = auto()
    Stench = auto()
    Drizzle = auto()
    SpeedBoost = auto()
    BattleArmor = auto()
    Sturdy = auto()
    Damp = auto()
    Limber = auto()
    SandVeil = auto()
    Static = auto()
    VoltAbsorb = auto()
    WaterAbsorb = auto()
    Oblivious = auto()
    CloudNine = auto()
    CompoundEyes = auto()
    Insomnia = auto()
    ColorChange = auto()
    Immunity = auto()
    FlashFire = auto()
    ShieldDust = auto()
    OwnTempo = auto()
    SuctionCups = auto()
    Intimidate = auto()
    ShadowTag = auto()
    RoughSkin = auto()
    WonderGuard = auto()
    Levitate = auto()
    EffectSpore = auto()
    Synchronize = auto()
    ClearBody = auto()
    NaturalCure = auto()
    LightningRod = auto()
    SereneGrace = auto()
    SwiftSwim = auto()
    Chlorophyll = auto()
    Illuminate = auto()
    Trace = auto()
    HugePower = auto()
    PoisonPoint = auto()
    InnerFocus = auto()
    MagmaArmor = auto()
    WaterVeil = auto()
    MagnetPull = auto()
    Soundproof = auto()
    RainDish = auto()
    SandStream = auto()
    Pressure = auto()
    ThickFat = auto()
    EarlyBird = auto()
    FlameBody = auto()
    RunAway = auto()
    KeenEye = auto()
    HyperCutter = auto()
    Pickup = auto()
    Truant = auto()
    Hustle = auto()
    CuteCharm = auto()
    Plus = auto()
    Minus = auto()
    Forecast = auto()
    StickyHold = auto()
    ShedSkin = auto()
    Guts = auto()
    MarvelScale = auto()
    LiquidOoze = auto()
    Overgrow = auto()
    Blaze = auto()
    Torrent = auto()
    Swarm = auto()
    RockHead = auto()
    Drought = auto()
    ArenaTrap = auto()
    VitalSpirit = auto()
    WhiteSmoke = auto()
    PurePower = auto()
    ShellArmor = auto()
    AirLock = auto()
    TangledFeet = auto()
    MotorDrive = auto()
    Rivalry = auto()
    Steadfast = auto()
    SnowCloak = auto()
    Gluttony = auto()
    AngerPoint = auto()
    Unburden = auto()
    Heatproof = auto()
    Simple = auto()
    DrySkin = auto()
    Download = auto()
    IronFist = auto()
    PoisonHeal = auto()
    Adaptability = auto()
    SkillLink = auto()
    Hydration = auto()
    SolarPower = auto()
    QuickFeet = auto()
    Normalize = auto()
    Sniper = auto()
    MagicGuard = auto()
    NoGuard = auto()
    Stall = auto()
    Technician = auto()
    LeafGuard = auto()
    Klutz = auto()
    MoldBreaker = auto()
    SuperLuck = auto()
    Aftermath = auto()
    Anticipation = auto()
    Forewarn = auto()
    Unaware = auto()
    TintedLens = auto()
    Filter = auto()
    SlowStart = auto()
    Scrappy = auto()
    StormDrain = auto()
    IceBody = auto()
    SolidRock = auto()
    SnowWarning = auto()
    HoneyGather = auto()
    Frisk = auto()
    Reckless = auto()
    Multitype = auto()
    FlowerGift = auto()
    BadDreams = auto()
    Pickpocket = auto()
    SheerForce = auto()
    Contrary = auto()
    Unnerve = auto()
    Defiant = auto()
    Defeatist = auto()
    CursedBody = auto()
    Healer = auto()
    FriendGuard = auto()
    WeakArmor = auto()
    HeavyMetal = auto()
    LightMetal = auto()
    Multiscale = auto()
    ToxicBoost = auto()
    FlareBoost = auto()
    Harvest = auto()
    Telepathy = auto()
    Moody = auto()
    Overcoat = auto()
    PoisonTouch = auto()
    Regenerator = auto()
    BigPecks = auto()
    SandRush = auto()
    WonderSkin = auto()
    Analytic = auto()
    Illusion = auto()
    Imposter = auto()
    Infiltrator = auto()
    Mummy = auto()
    Moxie = auto()
    Justified = auto()
    Rattled = auto()
    MagicBounce = auto()
    SapSipper = auto()
    Prankster = auto()
    SandForce = auto()
    IronBarbs = auto()
    ZenMode = auto()
    VictoryStar = auto()
    Turboblaze = auto()
    Teravolt = auto()
    AromaVeil = auto()
    FlowerVeil = auto()
    CheekPouch = auto()
    Protean = auto()
    FurCoat = auto()
    Magician = auto()
    Bulletproof = auto()
    Competitive = auto()
    StrongJaw = auto()
    Refrigerate = auto()
    SweetVeil = auto()
    StanceChange = auto()
    GaleWings = auto()
    MegaLauncher = auto()
    GrassPelt = auto()
    Symbiosis = auto()
    ToughClaws = auto()
    Pixilate = auto()
    Gooey = auto()
    Aerilate = auto()
    ParentalBond = auto()
    DarkAura = auto()
    FairyAura = auto()
    AuraBreak = auto()
    PrimordialSea = auto()
    DesolateLand = auto()
    DeltaStream = auto()
    Stamina = auto()
    WimpOut = auto()
    EmergencyExit = auto()
    WaterCompaction = auto()
    Merciless = auto()
    ShieldsDown = auto()
    Stakeout = auto()
    WaterBubble = auto()
    Steelworker = auto()
    Berserk = auto()
    SlushRush = auto()
    LongReach = auto()
    LiquidVoice = auto()
    Triage = auto()
    Galvanize = auto()
    SurgeSurfer = auto()
    Schooling = auto()
    Disguise = auto()
    BattleBond = auto()
    PowerConstruct = auto()
    Corrosion = auto()
    Comatose = auto()
    QueenlyMajesty = auto()
    InnardsOut = auto()
    Dancer = auto()
    Battery = auto()
    Fluffy = auto()
    Dazzling = auto()
    SoulHeart = auto()
    TanglingHair = auto()
    Receiver = auto()
    PowerofAlchemy = auto()
    BeastBoost = auto()
    RKSSystem = auto()
    ElectricSurge = auto()
    PsychicSurge = auto()
    MistySurge = auto()
    GrassySurge = auto()
    FullMetalBody = auto()
    ShadowShield = auto()
    PrismArmor = auto()
    Neuroforce = auto()
    IntrepidSword = auto()
    DauntlessShield = auto()
    Libero = auto()
    BallFetch = auto()
    CottonDown = auto()
    PropellerTail = auto()
    MirrorArmor = auto()
    GulpMissile = auto()
    Stalwart = auto()
    SteamEngine = auto()
    PunkRock = auto()
    SandSpit = auto()
    IceScales = auto()
    Ripen = auto()
    IceFace = auto()
    PowerSpot = auto()
    Mimicry = auto()
    ScreenCleaner = auto()
    SteelySpirit = auto()
    PerishBody = auto()
    WanderingSpirit = auto()
    GorillaTactics = auto()
    NeutralizingGas = auto()
    PastelVeil = auto()
    HungerSwitch = auto()
    QuickDraw = auto()
    UnseenFist = auto()
    CuriousMedicine = auto()
    Transistor = auto()
    DragonsMaw = auto()
    ChillingNeigh = auto()
    GrimNeigh = auto()
    AsOneI = auto()
    AsOneG = auto()