from tabnanny import verbose
from typing import Optional, List
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import os
import csv
from sklearn.cluster import estimate_bandwidth
from surprise import Reader
from surprise.model_selection import train_test_split
from utils import map_cat
import json
from surprise import dump
from surprise import KNNWithMeans
from surprise import Dataset

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================DATA=========================
data = pd.read_csv("book_infos.csv")

"""
=================== Body =============================
"""


class Book(BaseModel):
    book_author: str
    book_id: int
    book_title: str
    img_l: str
    publisher: str
    score: int
    year_of_publication: int
    


# == == == == == == == == == API == == == == == == == == == == =

# show five Category
@app.get("/api/Category")
def get_Category():
    return {'Category': ["Fiction", "Religion", "Biography_and_Autobiography", "Juvenile_Fiction", "History"]}


@app.post("/api/books")
def get_books(Category: list):
    query_str = " or ".join(map(map_cat, Category))
    results = data.query(query_str)
    results.loc[:, 'score'] = None
    results = results.sample(20, replace=False).loc[:, ['book_id', 'book_title', 'book_author', 'year_of_publication','publisher','img_l','score']]
    return json.loads(results.to_json(orient="records"))





@app.post("/api/recommend")
def get_recommend(books: List[Book]):
    tempiid = []
    tempscore = []
    for j in range(len(sorted(books, key=lambda i: i.score, reverse=True))):
        tempiid.append(sorted(books, key=lambda i: i.score, reverse=True)[j].book_id)
        tempscore.append(sorted(books, key=lambda i: i.score, reverse=True)[j].score)

    res = get_initial_items(tempiid,tempscore)

    res = [int(i) for i in res]
    if len(res) > 12:
        res = res[:12]

    rec_books = data.loc[data['book_id'].isin(res)]

    rec_books.loc[:, 'like'] = None
    results = rec_books.loc[:, ['book_id', 'book_title', 'book_author', 'year_of_publication','publisher','img_l', 'like']]
    
    return json.loads(results.to_json(orient="records"))




def get_initial_items(iid, score, n=12):
    res = []

    user_add(iid, score)

    file_path = os.path.expanduser('new_rating.data')
    reader = Reader(line_format='user item rating', sep=' ', rating_scale=(1,10))
    ratingData = Dataset.load_from_file(file_path, reader=reader)

    # Build train set and start the algorithms
    trainset = ratingData.build_full_trainset()
    algo = KNNWithMeans(sim_options={'name': 'cosine', 'user_based': False})
    algo.fit(trainset)
    dump.dump('./model',algo=algo,verbose=1)


    # Retrieve the iid of books in data set
    all_results = {}
    currList = []
    for i in data['book_id'].iteritems():
        cstr = str(i)
        cstr = cstr.replace(" ","")
        cstr=cstr.strip('(')
        cstr=cstr.strip(')')
        cstr=cstr.split(',')
        currList.append(str(cstr[1]))
        
    # Calculate the est of each book to user for prediction
    uid = str(100)
    for i in currList:
        iid = i
        pred = algo.predict(uid,iid).est
        all_results[iid] = pred

    
    # Sorted the predicted calulation result
    sorted_list = sorted(all_results.items(), key = lambda kv:(kv[1], kv[0]), reverse=True)

    for i in range(n):
        res.append(sorted_list[i][0])
    return res


def user_add(iid, score):
    user = '100'
    df = pd.read_csv('./rating.data')
    df.to_csv('new_' + 'rating.data')
    with open(r'new_rating.data',mode='a',newline='',encoding='utf8') as cfa:
        wf = csv.writer(cfa,delimiter=' ')
        data_input = []
        
        for i in range(len(iid)):
            s = [user,str(iid[i]),int(score[i])]
            data_input.append(s)
        
        for k in data_input:
            wf.writerow(k)



@app.get("/api/add_recommend/{item_id}")
async def add_recommend(item_id):
    res = get_similar_items(str(item_id), n=6)
    res = [int(i) for i in res]

    rec_books = data.loc[data['book_id'].isin(res)]

    rec_books.loc[:, 'like'] = None
    results = rec_books.loc[:, ['book_id', 'book_title', 'book_author', 'year_of_publication','publisher','img_l', 'like']]
    return json.loads(results.to_json(orient="records"))




def get_similar_items(iid, n=12):
    algo = dump.load('./model')[1]
    inner_id = algo.trainset.to_inner_iid(iid)
    neighbors = algo.get_neighbors(inner_id, k=n)
    neighbors_iid = [algo.trainset.to_raw_iid(x) for x in neighbors]
    return neighbors_iid