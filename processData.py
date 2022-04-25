import pandas as pd

book_df = pd.read_csv('book_info.csv')
rating_df = pd.read_csv('rating.csv')

book_df['Category'] = book_df.Category.str.split('|')

book_with_cat = book_df[['book_id','book_title','book_author','year_of_publication','publisher','Category','img_l']].copy(deep=True)


cat_list = []

for index, row in book_df.iterrows():
    for category in row['Category']:
        book_with_cat.at[index, category] = 1
        if category not in cat_list:
            cat_list.append(category)

book_with_cat = book_with_cat.fillna(0)

book_with_cat.to_csv("book_infos.csv")

print(cat_list)
