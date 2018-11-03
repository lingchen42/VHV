import os
from django.conf import settings
import ast
import json
import numpy as np
import random
from quickdraw.models import Drawing
from quickdraw.serializers import DrawingSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import generics
import gensim.downloader as gensimapi
from quickdraw.parse_sentence import *

# global parameters
print("Loading word2vec model")
WORD_MODEL = gensimapi.load("glove-wiki-gigaword-50")
print("Loading complete")
OBJS = [l.strip() for l in open(os.path.join(settings.PROJECT_ROOT, "objs_list.csv"))]
NLP = spacy.load('en')


def most_similar_word(word):
    most_sim_word = (np.inf, '')
    for obj in OBJS:
        dist = WORD_MODEL.wmdistance(word, obj)
        if dist < most_sim_word[0]:
            most_sim_word = (dist, obj)
    return most_sim_word[1]


def strokes2svgpath(strokes):
    svg_path = []
    for stroke in strokes:
        for ith, pos in enumerate(zip(stroke[0], stroke[1])):
            if ith == 0:
                p = "M%s %s"%(pos[0], pos[1])
            else:
                p = "L%s %s"%(pos[0], pos[1])
            svg_path.append(p)

    return " ".join(svg_path)


def process_sentence(sentence):
    doc = NLP(sentence)
    locs_d = sentence_to_loc(doc)
    mapped_locs_d = {}
    for key, item in locs_d.items():
        key = most_similar_word(key)
        mapped_locs_d[key] = item
    return mapped_locs_d

def word2Strokes(word):
    d = Drawing.objects.filter(word=word).order_by('?').first()
    serializer = DrawingSerializer(d)
    strokes = serializer.data['drawing']
    print(strokes)
    if isinstance(strokes, str):
        strokes = ast.literal_eval(strokes)
    return strokes

def locationDict(preposition): # maps prepositions to directions
    dict = {"on" : ["up"], "above":["up"],"under" : ["down"],"below":["down"],
        "beneath":["down"],"beside":["right","left"],"by":["left","right"],
        "against":["right","left"],"before":["left","right"],"after":["left","right"],
        "over":["up"],"alone":["alone"]}
    try:
        return random.choice(dict[preposition])
    except:
        return "alone"

def getMaxBound(strokes,coord):
    mx = 0
    if coord == "x":
        mx = max([max(stroke[0]) for stroke in strokes])
    else:
        mx = max([max(stroke[1]) for stroke in strokes])
    return mx

def adjustStrokes(strokes, amount, coord):
    if coord == "x":
        for stroke in strokes:
            stroke[0] = [x+amount for x in stroke[0]]
    else:
        for stroke in strokes:
            stroke[1] = [y+amount for y in stroke[1]]
    return strokes

def phrase2Strokes(object1,object2,loc): #object = dict key, loc= value
    location = locationDict(loc)
    print(object1, object2, location)
    if location == "up":
        strokes = word2Strokes(object1)
        strokes.extend(adjustStrokes(word2Strokes(object2),getMaxBound(strokes,"y"),"y"))
    elif location == "down":
        strokes = word2Strokes(object2)
        strokes.extend(adjustStrokes(word2Strokes(object1),getMaxBound(strokes,"y"),"y"))
    elif location == "right":
        strokes = word2Strokes(object2)
        strokes.extend(adjustStrokes(word2Strokes(object1),getMaxBound(strokes,"x"),"x"))
    elif location == "left":
        strokes = word2Strokes(object1)
        strokes.extend(adjustStrokes(word2Strokes(object2),getMaxBound(strokes,"y"),"x"))
    else:
        strokes = word2Strokes(object1)
    return strokes


@api_view(['GET'])
def DetailDrawing(request, sentence, format=None):
    """
    List all code snippets, or create a new snippet.
    """
    # TO DO tokenize, word2vector processing
    mapped_locs_d = process_sentence(sentence)
    print(mapped_locs_d)
    #try:
    drawn = []
    strokes = []
    for word1 in mapped_locs_d.keys():
        if word1 not in drawn:
            drawn.append(word1)
            print(mapped_locs_d[word1])
            for pair in mapped_locs_d[word1]:
                if pair[0] not in drawn:
                    drawn.append(pair[0])
                    strokes.extend(phrase2Strokes(word1,pair[0],pair[1]))
    path = strokes2svgpath(strokes)
    return Response([path])
    #except:
         # TO DO better error handling
    #    return Response("M150 0 L75 200 L225 200 Z")


class DrawingList(generics.ListCreateAPIView):
    queryset = Drawing.objects.all()
    serializer_class = DrawingSerializer
