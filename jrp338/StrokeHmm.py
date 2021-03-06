#Hidden Markov Models
#-------------------------------------------------
#Jeanette Pranin (jrp338)
#Jaiveer Kothari (jvk383)
#Nishant Subramani (nso155)


import xml.dom.minidom
import copy
import guid
import math
import os
import numpy

# A couple contants
CONTINUOUS = 0
DISCRETE = 1

class HMM:
    ''' Code for a hidden Markov Model '''

    def __init__(self, states, features, contOrDisc, numVals):
        ''' Initialize the HMM.
            Input:
                states: a list of the hidden state possible values
                features: a list of feature names
                contOrDisc: a dictionary mapping feature names to integers
                    representing whether the feature is continuous or discrete
                numVals: a dictionary mapping names of discrete features to
                    the number of values that feature can take on. '''
        self.states = states 
        self.isTrained = False
        self.featureNames = features
        self.featuresCorD = contOrDisc
        self.numVals = numVals

        #added field called featureIndices that will keep track of which feature option corresponds with which index
        self.featureIndices = {}

        # All the probabilities start uninitialized until training
        self.priors = None
        self.emissions = None   #evidence model
        self.transitions = None #transition model

    def train(self, trainingData, trainingLabels):
        ''' Train the HMM on the fully observed data using MLE '''
        print "Training the HMM... "
        self.isTrained = True
        self.trainPriors( trainingData, trainingLabels )
        self.trainTransitions( trainingData, trainingLabels )
        self.trainEmissions( trainingData, trainingLabels ) 
        print "HMM trained"
        print "Prior probabilities are:", self.priors
        print "Transition model is:", self.transitions
        print "Evidence model is:", self.emissions

    def trainPriors( self, trainingData, trainingLabels ):
        ''' Train the priors based on the data and labels '''
        # Set the prior probabilities
        priorCounts = {}
        for s in self.states:
            priorCounts[s] = 0
        for labels in trainingLabels:
            priorCounts[labels[0]] += 1

        self.priors = {}
        for s in self.states:
            self.priors[s] = float(priorCounts[s])/len(trainingLabels)
        

    def trainTransitions( self, trainingData, trainingLabels ):
        ''' Give training data and labels, train the transition model '''
        # Set the transition probabilities
        # First initialize the transition counts
        transitionCounts = {}
        for s in self.states:
            transitionCounts[s] = {}
            for s2 in self.states:
                transitionCounts[s][s2] = 0
                
        for labels in trainingLabels:
            if len(labels) > 1:
                lab1 = labels[0]
                for lab2 in labels[1:]:
                    transitionCounts[lab1][lab2] += 1
                    lab1 = lab2
                    
        self.transitions = {}
        for s in transitionCounts.keys():
            self.transitions[s] = {}
            totForS = sum(transitionCounts[s].values())
            for s2 in transitionCounts[s].keys():
                self.transitions[s][s2] = float(transitionCounts[s][s2])/float(totForS)


    def trainEmissions( self, trainingData, trainingLabels ):
        ''' given training data and labels, train the evidence model.  '''
        self.emissions = {}
        featureVals = {}
        for s in self.states:
            self.emissions[s] = {}
            featureVals[s] = {}
            for f in self.featureNames:
                featureVals[s][f] = []

        # Now gather the features for each state
        for i in range(len(trainingData)):
            oneSketchFeatures = trainingData[i]
            oneSketchLabels = trainingLabels[i]
            
            for j in range(len(oneSketchFeatures)):
                features = oneSketchFeatures[j]
                for f in features.keys():
                    featureVals[oneSketchLabels[j]][f].append(features[f])

        # Do a slightly different thing for continuous vs. discrete features
        for s in featureVals.keys():
            for f in featureVals[s].keys():
                if self.featuresCorD[f] == CONTINUOUS:
                    # Use a gaussian representation, so just find the mean and standard dev of the data
                    # mean is just the sample mean
                    mean = sum(featureVals[s][f])/len(featureVals[s][f])
                    sigmasq = sum([(x - mean)**2 for x in featureVals[s][f]]) / len(featureVals[s][f])
                    sigma = math.sqrt(sigmasq)
                    self.emissions[s][f] = [mean, sigma]
                if self.featuresCorD[f] == DISCRETE:
                    # If the feature is discrete then the CPD is a list
                    # We assume that feature values are integer, starting
                    # at 0.  This assumption could be generalized.
                    counter = 0
                    self.emissions[s][f] = [1]*self.numVals[f]  # Use add 1 smoothing
                    for fval in featureVals[s][f]:
                        self.emissions[s][f][fval] += 1
                    # Now we have counts of each feature and we need to normalize
                    for i in range(len(self.emissions[s][f])):
                        self.emissions[s][f][i] /= float(len(featureVals[s][f])+self.numVals[f])

              
    def label( self, data ):

        ''' Find the most likely labels for the sequence of data
            This is an implementation of the Viterbi algorithm '''

        #Debugging tools to help see what is being accessed
        # print "Data is: " + str(data)
        # print "States are: " + str(self.states)
        # print "FeatureNames are: " + str(self.featureNames)
        # print "Emissions are: " + str(self.emissions)
        # print "Feature Indices are " + str(self.featureIndices)
        # print "Transitions are " + str(self.transitions)
        # print "States are " + str(self.states)
        # print "------------------------------------------------------"

        #creates a list of dictionaries that will hold the partial probabilities of each state
        #viterbi_calc will be used to refer to the prior partial probabilities in the code below
        viterbi_calc = [{}]
        path = {}

        #calculating partial probability of first day/state
        for state in self.states:

            #keeps tracks of the evidence probability of every feature
            first_feature_vals = []

            for f in self.featureNames:
                #gets the value of the feature f at first day
                first_value = data[0][f]

                #gets the index of the feature f (e.g. Dry's index is 0, Dryish's index is 1, etc.)
                index = self.featureIndices[f][first_value]

                #add to the feature_vals
                first_feature_vals.append(self.emissions[state][f][index])

            #can multiply the probabilities together because we assume they are independent
            first_evi = 1
            for feat in first_feature_vals:
                first_evi *= feat

            #calculates the partial probability at the first step
            viterbi_calc[0][state] = self.priors[state] * first_evi

            #puts the current state as the first step in the path of the current state
            path[state] = [state]


        #Run Viterbi for t > 0
        #counter = 0
        for t in range(1, len(data)):
            #add new dictionaries
            viterbi_calc.append({})
            new_path = {}


            for y in self.states:
                curr_feature_vals = []

                for f0 in self.featureNames:
                    #gets the value of the feature f at day t
                    curr_val = data[t][f0]

                    #gets the index of the feature f (e.g. Dry's index is 0, Dryish's index is 1, etc.)
                    idx = self.featureIndices[f0][curr_val]

                    curr_feature_vals.append(self.emissions[y][f0][idx])
                curr_evi = 1
                for curr_feat in curr_feature_vals:
                    curr_evi *= curr_feat

                #gets the max partial probability of the current state
                (prob, state) = max((viterbi_calc[t-1][y0]*self.transitions[y0][y]*curr_evi, y0) for y0 in self.states)

                #assigns prob (the partial probability of the current state) to the viterbi calculation dictionary and keeps track of the paths taken so far
                viterbi_calc[t][y] = prob

                #keep track of the paths so far
                new_path[y] = path[state] + [y]

            #don't have to remember old path
            path = new_path

            
        #gets the max viterbi calculation with its accompanying best path
        (prob, state) = max((viterbi_calc[t][s1], s1) for s1 in self.states)

        print "Best path is: " + str(path[state])
        print "Prob of best path is: " + str(prob)

        return path[state]




    
    def getEmissionProb( self, state, features ):
        ''' Get P(features|state).
            Consider each feature independent so
            P(features|state) = P(f1|state)*P(f2|state)*...*P(fn|state). '''
        prob = 1.0
        for f in features:
            if self.featuresCorD[f] == CONTINUOUS:
                # calculate the gaussian prob
                fval = features[f]
                mean = self.emissions[state][f][0]
                sigma = self.emissions[state][f][1]
                g = math.exp((-1*(fval-mean)**2) / (2*sigma**2))
                g = g / (sigma * math.sqrt(2*math.pi))
                prob *= g
            if self.featuresCorD[f] == DISCRETE:
                fval = features[f]
                prob *= self.emissions[state][f][fval]
                
        return prob
        





class StrokeLabeler:
    def __init__(self):
        ''' Inialize a stroke labeler. '''
        self.labels = ['text', 'drawing']
        # a map from labels in files to labels we use here
        drawingLabels = ['Wire', 'AND', 'OR', 'XOR', 'NAND', 'NOT']
        textLabels = ['Label']
        self.labels = ['drawing', 'text']


        #added field called featureIndices that will keep track of which feature option corresponds with which index
        self.featureIndices = {}
        
        self.labelDict = {}
        for l in drawingLabels:
            self.labelDict[l] = 'drawing'
        for l in textLabels:
            self.labelDict[l] = 'text'

        # Define the features to be used in the featurefy function
        # if you change the featurefy function, you must also change
        # these data structures.
        # featureNames is just a list of all features.
        # contOrDisc is a dictionary mapping each feature
        #    name to whether it is continuous or discrete
        # numFVals is a dictionary specifying the number of legal values for
        #    each discrete feature
        
        # self.featureNames = ['x']
        # self.contOrDisc = {'x' : DISCRETE}
        # self.numFVals = {'x' : 4}
        # self.numFVals = {'x' : 2}
        # self.featureNames = ['draw_speed']
        # self.contOrDisc = {'draw_speed' : DISCRETE}
        # self.numFVals = {'draw_speed' : 4}

        # self.featureNames = ['nearest_neighbor_dist']
        # self.contOrDisc = {'nearest_neighbor_dist' : DISCRETE}
        # self.numFVals = {'nearest_neighbor_dist' : 2}
        
        #all 5 features together
        self.featureNames = ['length', 'nearest_neighbor_dist', 'draw_speed', 'x', 'bb_area']
        self.contOrDisc = {'length': DISCRETE, 'nearest_neighbor_dist' : DISCRETE, 'draw_speed' : DISCRETE, 'x' : DISCRETE, 'bb_area' : DISCRETE}
        self.numFVals = { 'length': 2, 'nearest_neighbor_dist' : 2, 'draw_speed' : 4, 'x' : 4, 'bb_area' : 4}

        # self.featureNames = ['bb_area']
        # self.contOrDisc = {'bb_area' : DISCRETE}
        # self.numFVals = {'bb_area' : 4}

    def featurefy( self, strokes ):
        ''' Converts the list of strokes into a list of feature dictionaries
            suitable for the HMM
            The names of features used here have to match the names
            passed into the HMM'''
        ret = []
        d = {}  # The feature dictionary to be returned for one stroke

        #creating a feature that calculates proximity to nearest neighbor
        #This feature calculates the euclidean distance between starting location of stroke s and s2 and finds the smallest distance between
        #s and any other s2. These distances were binned around the mean, with anything less being binned as a 0 and anything greater being binned
        #as a 1.
        sum_dist = 0
        mean_dist = None
        stroke_dist = []
        draw_speed = []
        sum_speed = 0
        mean_speed = None
        x_coord = []
        bounding_box_area = []
        for s in strokes: #loop through all strokes
            closest_stroke_dist = 1000000
            start_pt = s.points[0] #find the first pt
            start_time = s.points[0][-1] #find the start time of a stroke
            end_time = s.points[-1][-1] #find the end time
            speed = (end_time - start_time)/float(len(s.points)) #find the actual time per point in the stroke
            #print "Speed " + str(speed)
            draw_speed.append(speed) #add it in
            sum_speed += speed
            xx = 0
            #bounding box area calc
            min_x = 1000000
            max_x = -1000000
            min_y = 1000000
            max_y = -1000000
            for k in range(len(s.points)):
                #find the x and y coordinate of each point on the stroke
                x = s.points[k][0]
                y = s.points[k][1]
                if x < min_x:
                    min_x = x

                if x > max_x:
                    max_x = x

                if y < min_y:
                    min_y = y

                if y > max_y:
                    max_y = y
                #check if its dimensions are larger/smaller than the max and min
                xx += s.points[k][0]
            x_coord.append(xx/float(len(s.points))) #add the average x coordinate to the list
            bb_area = (max_y - min_y) * (max_x - min_x) #calc bounding box area and add to bb_area list
            bounding_box_area.append(bb_area)
    
            for s2 in strokes: #loop through all strokes for tuples
                if s != s2:
                    max_idx = len(s2.points)
                    for j in range(1,max_idx):
                        s2_pt = s2.points[j]
                        xdiff = start_pt[0] - s2_pt[0]
                        ydiff = start_pt[1] - s2_pt[1]

                        dist = math.sqrt(xdiff**2 + ydiff**2) #calculates distance
                        if dist < closest_stroke_dist: #checks if its better than previous
                            closest_stroke_dist = dist
            sum_dist += closest_stroke_dist #sum the distances
            stroke_dist.append(closest_stroke_dist) #add it to a list

        mean_dist = sum_dist/len(strokes) #calculate the threshold/bin value

        #calculates all the bin values
        q1_speed = numpy.percentile(draw_speed, 25)
        median_speed = numpy.percentile(draw_speed, 50)
        q3_speed = numpy.percentile(draw_speed, 75)
        mean_speed = sum_speed/len(strokes)
        median_dist = numpy.percentile(stroke_dist, 50)
        q1_x = numpy.percentile(x_coord, 25)
        median_x = numpy.percentile(x_coord, 50)
        q3_x = numpy.percentile(x_coord, 75)
        q1_bb = numpy.percentile(bounding_box_area, 25)
        bb_median = numpy.percentile(bounding_box_area, 50)
        q3_bb = numpy.percentile(bounding_box_area, 75)
        bb_mean = numpy.mean(bounding_box_area)           




        #bin the features   
        for i in range(len(strokes)):    
            l = strokes[i].length()
            if l < 300:
                d['length'] = 0
            else:
                d['length'] = 1

            dist = stroke_dist[i]
            if dist < median_dist:
                d['nearest_neighbor_dist'] = 0
            else:
                d['nearest_neighbor_dist'] = 1

            sp = draw_speed[i]
            if sp < q1_speed:
                d['draw_speed'] = 0
            elif sp < median_speed:
                d['draw_speed'] = 1
            elif sp < q3_speed:
                d['draw_speed'] = 2
            else:
                d['draw_speed'] = 3

            xxx = x_coord[i]
            if xxx < q1_x:
                d['x'] = 0
            elif xxx < median_x:
                d['x'] = 1
            elif xxx < q3_x:
                d['x'] = 2
            else:
                d['x'] = 3

            bb = bounding_box_area[i]
            if bb < q1_bb:
                d['bb_area'] = 0
            elif bb < bb_median:
                d['bb_area'] = 1
            elif bb < q3_bb:
                d['bb_area'] = 2
            else:
                d['bb_area'] = 3
            


            ret.append(d)  # append the feature dictionary to the list

        #adds the featureIndices of each feature
        self.featureIndices['length'] = {0: 0, 1: 1}
        self.featureIndices['nearest_neighbor_dist'] = {0: 0, 1: 1}
        self.featureIndices['draw_speed'] = {0: 0, 1: 1, 2: 2, 3: 3}
        self.featureIndices['x'] = {0: 0, 1: 1, 2: 2, 3: 3}
        self.featureIndices['bb_area'] = {0: 0, 1: 1, 2: 2, 3: 3}
        return ret
    
    def trainHMM( self, trainingFiles ):
        ''' Train the HMM '''
        self.hmm = HMM( self.labels, self.featureNames, self.contOrDisc, self.numFVals )
        allStrokes = []
        allLabels = []
        for f in trainingFiles:
            print "Loading file", f, "for training"
            strokes, labels = self.loadLabeledFile( f )
            allStrokes.append(strokes)
            allLabels.append(labels)
        allObservations = [self.featurefy(s) for s in allStrokes]
        self.hmm.train(allObservations, allLabels)

    def trainHMMDir( self, trainingDir ):
        ''' train the HMM on all the files in a training directory '''
        for fFileObj in os.walk(trainingDir):
            lFileList = fFileObj[2]
            break
        goodList = []
        for x in lFileList:
            if not x.startswith('.'):
                goodList.append(x)
        
        tFiles = [ trainingDir + "/" + f for f in goodList ] 
        self.trainHMM(tFiles)

    def featureTest( self, strokeFile ):
        ''' Loads a stroke file and tests the feature functions '''
        strokes, labels = self.loadLabeledFile( strokeFile )
        for i in range(len(strokes)):
            print " "
            print strokes[i].substrokeIds[0]
            print "Label is", labels[i]
            print "Length is", strokes[i].length()
            print "Curvature is", strokes[i].sumOfCurvature(abs)
    
    def labelFile( self, strokeFile, outFile ):
        ''' Label the strokes in the file strokeFile and save the labels
            (with the strokes) in the outFile '''
        print "Labeling file", strokeFile
        strokes = self.loadStrokeFile( strokeFile )
        labels = self.labelStrokes( strokes )
        print "Labeling done, saving file as", outFile
        self.saveFile( strokes, labels, strokeFile, outFile )

    def labelStrokes( self, strokes ):
        ''' return a list of labels for the given list of strokes '''
        if self.hmm == None:
            print "HMM must be trained first"
            return []
        strokeFeatures = self.featurefy(strokes)
        self.hmm.featureIndices = self.featureIndices
        return self.hmm.label(strokeFeatures)


    def confusion(self, trueLabels, classifications):
        len_trueLabels = len(trueLabels)
        len_classifications = len(classifications)

        if len_trueLabels != len_classifications:
            print "Truth Labels and Classifications are different lengths. Check inputs."
            return None


        confusion_matrix = {l: {} for l in self.labels}

        for entry in confusion_matrix:
            confusion_matrix[entry] = {l: 0 for l in self.labels}
        
        
        for i in range(len_trueLabels):
            t = trueLabels[i]
            c = classifications[i]
            if t == c:
                confusion_matrix[t][t] += 1
            else:
                confusion_matrix[t][c] += 1

        print "Confusion Matrix is: " + str(confusion_matrix)
        return confusion_matrix




    def saveFile( self, strokes, labels, originalFile, outFile ):
        ''' Save the labels of the stroke objects and the stroke objects themselves
            in an XML format that can be visualized by the labeler.
            Need to input the original file from which the strokes were read
            so that we can retrieve a lot of data that we don't store here'''
        sketch = xml.dom.minidom.parse(originalFile)
        # copy most of the data, including all points, substrokes, strokes
        # then just add the shapes onto the end
        impl =  xml.dom.minidom.getDOMImplementation()
        
        newdoc = impl.createDocument(sketch.namespaceURI, "sketch", sketch.doctype)
        top_element = newdoc.documentElement

        # Add the attibutes from the sketch document
        for attrib in sketch.documentElement.attributes.keys():
            top_element.setAttribute(attrib, sketch.documentElement.getAttribute(attrib))

        # Now add all the children from sketch as long as they are points, strokes
        # or substrokes
        sketchElem = sketch.getElementsByTagName("sketch")[0]
        for child in sketchElem.childNodes:
            if child.nodeType == xml.dom.Node.ELEMENT_NODE:
                if child.tagName == "point":
                    top_element.appendChild(child)
                elif child.tagName == "shape":
                    if child.getAttribute("type") == "substroke" or \
                       child.getAttribute("type") == "stroke":
                        top_element.appendChild(child)    

        # Finally, add the new elements for the labels
        for i in range(len(strokes)):
            # make a new element
            newElem = newdoc.createElement("shape")
            # Required attributes are type, name, id and time
            newElem.setAttribute("type", labels[i])
            newElem.setAttribute("name", "shape")
            newElem.setAttribute("id", guid.generate() )
            newElem.setAttribute("time", str(strokes[i].points[-1][2]))  # time is finish time

            # Now add the children
            for ss in strokes[i].substrokeIds:
                ssElem = newdoc.createElement("arg")
                ssElem.setAttribute("type", "substroke")
                ssElem.appendChild(newdoc.createTextNode(ss))
                newElem.appendChild(ssElem)
                
            top_element.appendChild(newElem)
            

        # Write to the file
        filehandle = open(outFile, "w")
        newdoc.writexml(filehandle)
        filehandle.close()

        # unlink the docs
        newdoc.unlink()
        sketch.unlink()

    def loadStrokeFile( self, filename ):
        ''' Read in a file containing strokes and return a list of stroke
            objects '''
        sketch = xml.dom.minidom.parse(filename)
        # get the points
        points = sketch.getElementsByTagName("point")
        pointsDict = self.buildDict(points)
    
        # now get the strokes by first getting all shapes
        allShapes = sketch.getElementsByTagName("shape")
        shapesDict = self.buildDict(allShapes)

        strokes = []
        for shape in allShapes:
            if shape.getAttribute("type") == "stroke":
                strokes.append(self.buildStroke( shape, shapesDict, pointsDict ))

        # I THINK the strokes will be loaded in order, but make sure
        if not self.verifyStrokeOrder(strokes):
            print "WARNING: Strokes out of order"

        sketch.unlink()
        return strokes

    def verifyStrokeOrder( self, strokes ):
        ''' returns True if all of the strokes are temporally ordered,
            False otherwise. '''
        time = 0
        ret = True
        for s in strokes:
            if s.points[0][2] < time:
                ret = False
                break
            time = s.points[0][2]
        return ret

    def buildDict( self, nodesWithIdAttrs ):
        ret = {}
        for n in nodesWithIdAttrs:
            idAttr = n.getAttribute("id")
            ret[idAttr] = n
        
        return ret

    def buildStroke( self, shape, shapesDict, pointDict ):
        ''' build and return a stroke object by finding the substrokes and points
            in the shape object '''
        ret = Stroke( shape.getAttribute("id") )
        points = []
        # Get the children of the stroke
        last = None
        for ss in shape.childNodes:
            if ss.nodeType != xml.dom.Node.ELEMENT_NODE \
               or ss.getAttribute("type") != "substroke":
                continue

            # Add the substroke id to the stroke object
            ret.addSubstroke(ss.firstChild.data)
            
            # Find the shape with the id of this substroke
            ssShape = shapesDict[ss.firstChild.data]

            # now get all the points associated with this substroke
            # We'll filter points that don't move here
            for ptObj in ssShape.childNodes:
                if ptObj.nodeType != xml.dom.Node.ELEMENT_NODE \
                   or ptObj.getAttribute("type") != "point":
                    continue
                pt = pointDict[ptObj.firstChild.data]
                x = int(pt.getAttribute("x"))
                y = int(pt.getAttribute("y"))
                time = int(pt.getAttribute("time"))
                if last == None or last[0] != x or last[1] != y:  # at least x or y is different
                    points.append((x, y, time))
                    last = (x, y, time)
        ret.setPoints(points)
        return ret
                

    def loadLabeledFile( self, filename ):
        ''' load the strokes and the labels for the strokes from a labeled file.
            return the strokes and the labels as a tuple (strokes, labels) '''
        sketch = xml.dom.minidom.parse(filename)
        # get the points
        points = sketch.getElementsByTagName("point")
        pointsDict = self.buildDict(points)
    
        # now get the strokes by first getting all shapes
        allShapes = sketch.getElementsByTagName("shape")
        shapesDict = self.buildDict(allShapes)

        strokes = []
        substrokeIdDict = {}
        for shape in allShapes:
            if shape.getAttribute("type") == "stroke":
                stroke = self.buildStroke( shape, shapesDict, pointsDict )
                strokes.append(self.buildStroke( shape, shapesDict, pointsDict ))
                substrokeIdDict[stroke.strokeId] = stroke
            else:
                # If it's a shape, then just store the label on the substrokes
                for child in shape.childNodes:
                    if child.nodeType != xml.dom.Node.ELEMENT_NODE \
                       or child.getAttribute("type") != "substroke":
                        continue
                    substrokeIdDict[child.firstChild.data] = shape.getAttribute("type")

        # I THINK the strokes will be loaded in order, but make sure
        if not self.verifyStrokeOrder(strokes):
            print "WARNING: Strokes out of order"

        # Now put labels on the strokes
        labels = []
        noLabels = []
        for stroke in strokes:
            # Just give the stroke the label of the first substroke in the stroke
            ssid = stroke.substrokeIds[0]
            if not self.labelDict.has_key(substrokeIdDict[ssid]):
                # If there is no label, flag the stroke for removal
                noLabels.append(stroke)
            else:
                labels.append(self.labelDict[substrokeIdDict[ssid]])

        for stroke in noLabels:
            strokes.remove(stroke)
            
        sketch.unlink()
        if len(strokes) != len(labels):
            print "PROBLEM: number of strokes and labels must match"
            print "numStrokes is", len(strokes), "numLabels is", len(labels)
        return strokes, labels

class Stroke:
    ''' A class to represent a stroke (series of xyt points).
        This class also has various functions for computing stroke features. '''
    def __init__(self, strokeId):
        self.strokeId = strokeId
        self.substrokeIds = []   # Keep around the substroke ids for writing back to file
        
    def __repr__(self):
        ''' Return a string representation of the stroke '''
        return "[Stroke " + self.strokeId + "]"

    def addSubstroke( self, substrokeId ):
        ''' Add a substroke Id to the stroke '''
        self.substrokeIds.append(substrokeId)

    def setPoints( self, points ):
        ''' Set the points for the stroke '''
        self.points = points


    # Feature functions follow this line
    def length( self ):
        ''' Returns the length of the stroke '''
        ret = 0
        prev = self.points[0]
        for p in self.points[1:]:
            # use Euclidean distance
            xdiff = p[0] - prev[0]
            ydiff = p[1] - prev[1]
            ret += math.sqrt(xdiff**2 + ydiff**2)
            prev = p
        return ret



    def sumOfCurvature(self, func=lambda x: x, skip=1):
        ''' Return the normalized sum of curvature for a stroke.
            func is a function to apply to the curvature before summing
                e.g., to find the sum of absolute value of curvature,
                you could pass in abs
            skip is a smoothing constant (how many points to skip)
        '''
        if len(self.points) < 2*skip+1:
            return 0
        ret = 0
        second = self.points[0]
        third = self.points[1*skip]
        for p in self.points[2*skip::skip]:
            
            first = second
            second = third
            third = p
            ax = second[0] - first[0]
            ay = second[1] - first[1]
            bx = third[0] - second[0]
            by = third[1] - second[1]
            
            lena = math.sqrt(ax**2 + ay**2)
            lenb = math.sqrt(bx**2 + by**2)

            dotab = ax*bx + ay*by
            arg = float(dotab)/float(lena*lenb)

            # Fix floating point precision errors
            if arg > 1.0:
                arg = 1.0
            if arg < -1.0:
                arg = -1.0

            curv = math.acos(arg)

            # now we have to find the sign of the curvature
            # get the angle betwee the first vector and the x axis
            anga = math.atan2(ay, ax)
            # and the second
            angb = math.atan2(by, bx)
            # now compare them to get the sign.
            if not(angb < anga and angb > anga-math.pi):
                curv *= -1
            ret += func(curv)

        return ret / len(self.points)

    # You can (and should) define more features here


def test_trainHMM():
    '''
    Part 1 Viterbi Testing Example: Dry, Dryish, Damp, Soggy Seaweed Example
    '''
    test_states = ['Sunny', 'Cloudy', 'Rainy']
    test_features = ['Wetness']
    test_contOrDisc = {'Wetness': DISCRETE}
    test_numVals = {'Wetness': 4}

    test_hmm = HMM(test_states, test_features, test_contOrDisc, test_numVals)
    test_hmm.priors = {'Sunny': 0.63, 'Cloudy': 0.17, 'Rainy': 0.20}
    test_hmm.transitions = {'Sunny': {'Sunny': 0.500, 'Cloudy': 0.25, 'Rainy': 0.25}, \
                             'Cloudy': {'Sunny': 0.375, 'Cloudy': 0.125, 'Rainy': 0.375}, \
                             'Rainy': {'Sunny': 0.125, 'Cloudy': 0.675, 'Rainy': 0.375}}
    test_hmm.emissions = {'Sunny': {'Wetness': [0.60, 0.20, 0.15, 0.05]}, \
                            'Cloudy': {'Wetness': [0.25, 0.25, 0.25, 0.25]}, \
                            'Rainy': {'Wetness': [0.05, 0.10, 0.35, 0.50]}}

    

    test_sequence = [{'Wetness': 'Dry'}, {'Wetness': 'Damp'}, {'Wetness': 'Soggy'}]

    #Dry will be the 0th index of the features list, Dry's index will be 1, etc.
    test_hmm.featureIndices['Wetness'] = {'Dry': 0, 'Dryish': 1, 'Damp': 2, 'Soggy': 3}
    return test_hmm.label(test_sequence)


##############CODE FOR RESULTS.TXT AND CONFUSION MATRIX##############
# sl = StrokeLabeler()

# #training files
# sl.trainHMMDir("../trainForResults/")

# true_labels = []
# classifications_labels = []

# for fFileObj in os.walk("../testForResults/"):
#     lFileList = fFileObj[2]
#     break


# goodList = []
# for x in lFileList:
#     if not x.startswith('.'):
#         goodList.append(x)

# tFiles = [ "../testForResults/" + "/" + f for f in goodList ] 

# for test_file in tFiles:

#     strokes, labels = sl.loadLabeledFile(test_file)
#     true_labels.extend(labels)

#     mylabels = sl.labelStrokes(strokes)
#     classifications_labels.extend(mylabels)

# big_confusion_matrix = sl.confusion(true_labels, classifications_labels)

# print "------------------------------------------------------"
# print "BIG CONFUSION MATRIX"
# print big_confusion_matrix

##################TESTING ON SEAWEED EXAMPLE FROM CLASS####################
# print "------------------------------------------------------"
# print "------------------------------------------------------"
# print "------------------------------------------------------"
# test_trainHMM()

