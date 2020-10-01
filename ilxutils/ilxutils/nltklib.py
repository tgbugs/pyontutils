'''
nltk.download(['wordnet', 'stopwords', 'punkt']) if not already downloaded.
Should add to wordnet if you want more words to compare as reference to.
'''
from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from fuzzywuzzy import fuzz, process
stop_words = stopwords.words('english')


states = {
    'ak': 'alaska',
    'al': 'alabama',
    'ar': 'arkansas',
    'as': 'american samoa',
    'az': 'arizona',
    'ca': 'california',
    'co': 'colorado',
    'ct': 'connecticut',
    'dc': 'district of columbia',
    'de': 'delaware',
    'fl': 'florida',
    'ga': 'georgia',
    'gu': 'guam',
    'hi': 'hawaii',
    'ia': 'iowa',
    'id': 'idaho',
    'il': 'illinois',
    'in': 'indiana',
    'ks': 'kansas',
    'ky': 'kentucky',
    'la': 'louisiana',
    'ma': 'massachusetts',
    'md': 'maryland',
    'me': 'maine',
    'mi': 'michigan',
    'mn': 'minnesota',
    'mo': 'missouri',
    'mp': 'northern mariana islands',
    'ms': 'mississippi',
    'mt': 'montana',
    'na': 'national',
    'nc': 'north carolina',
    'nd': 'north dakota',
    'ne': 'nebraska',
    'nh': 'new hampshire',
    'nj': 'new jersey',
    'nm': 'new mexico',
    'nv': 'nevada',
    'ny': 'new york',
    'oh': 'ohio',
    'ok': 'oklahoma',
    'or': 'oregon',
    'pa': 'pennsylvania',
    'pr': 'puerto rico',
    'ri': 'rhode island',
    'sc': 'south carolina',
    'sd': 'south dakota',
    'tn': 'tennessee',
    'tx': 'texas',
    'ut': 'utah',
    'va': 'virginia',
    'vi': 'virgin islands',
    'vt': 'vermont',
    'wa': 'washington',
    'wi': 'wisconsin',
    'wv': 'west virginia',
    'wy': 'wyoming'
}

def penn_to_wn(tag):
    """ Convert between a Penn Treebank tag to a simplified Wordnet tag """
    if tag.startswith('N'):
        return 'n'

    if tag.startswith('V'):
        return 'v'

    if tag.startswith('J'):
        return 'a'

    if tag.startswith('R'):
        return 'r'

    return None

def tagged_to_synset(word, tag):
    wn_tag = penn_to_wn(tag)
    # wn_tag is None if no definition is found
    if wn_tag is None:
        return word
    # try:
        # most probable english word
    return wn.synsets(word, wn_tag)[0]
    # except:
    #     return word

def fix_state_abbrev(tokens):
    token = [
        states[token] if states.get(token) else token
        for token in tokens
    ]
    return token

def clean_tokens(tokens, ignore_integers=False):
    punctuations = ['(',')',';',':','[',']',',','.','/']
    keywords = [
        word for word in tokens
        if not word in stop_words and not word in punctuations
    ]
    keywords = fix_state_abbrev(keywords)
    if ignore_integers:
        keywords = [word for word in keywords if not is_possible_integer(word)]
    return keywords

def clean(word):
    word = str(word).lower().strip()
    punctuations = ['(',')',';',':','[',']',',','.','/']
    for punctuation in punctuations:
        word = word.replace(punctuation, '')
    return word

def is_possible_integer(word):
    try:
        int(word)
        return True
    except:
        return False

def sentence_similarity(sentence1, sentence2, ignore_integers=False):
    """ compute the sentence similarity using Wordnet """
    # Tokenize and tag
    sentence1 = ' '.join([clean(word) for word in sentence1.split()])
    sentence2 = ' '.join([clean(word) for word in sentence2.split()])
    tokens1 = word_tokenize(sentence1)
    tokens2 = word_tokenize(sentence2)
    tokens1 = clean_tokens(tokens1, ignore_integers)
    tokens2 = clean_tokens(tokens2, ignore_integers)

    # tag
    sentence1 = pos_tag(tokens1)
    sentence2 = pos_tag(tokens2)

    # Get the synsets for the tagged words
    synsets1 = [tagged_to_synset(*tagged_word) for tagged_word in sentence1]
    synsets2 = [tagged_to_synset(*tagged_word) for tagged_word in sentence2]
    print(synsets1)
    print(synsets2)
    # Filter out the Nones
    synsets1 = [ss for ss in synsets1 if ss]
    synsets2 = [ss for ss in synsets2 if ss]

    score, count = 0.0, 0.0

    # For each word in the first sentence
    for synset1 in synsets1:
        # Get the similarity value of the most similar word in the other sentence
        best_score=[
            wn.path_similarity(synset1, synset2)
            if not isinstance(synset1, str) and not isinstance(synset2, str)
            # just in case there are scientific words wordnet does not have
            else fuzz.ratio(str(synset1), str(synset2)) / 100
            for synset2 in synsets2
        ]
        best_score=[s if s else 0 for s in best_score]
        # print(synsets1, synsets2)
        # Check that the similarity could have been computed
        if best_score:
            score += max(best_score)
            count += 1

    # Average the values
    if count > 0:
        score /= count
    else:
        score = 0

    return score

def get_tokenized_sentence(sentence):
    # Tokenize and tag
    sentence = pos_tag(word_tokenize(sentence))
    # Get the synsets for the tagged words
    synsets = []
    for tagged_word in sentence:
        synset = tagged_to_synset(*tagged_word)
        if synset:
            synsets.append(synset)
        else:
            synsets.append(tagged_word[0])
    return synsets # str(sorted(synsets))

def main():
    sentences = [
        "life is good in pa 92092",
        "life is good in pa",
        "life is good within pa 92092/2",
        "life is good pa 92092/2",
        "life is good in pa 92092/2",
        "testing for difference"
    ]
    focus_sentence = "life is good in pennsylvania"

    for sentence in sentences:
        # print ("Similarity(\"%s\", \"%s\") = %s" % (focus_sentence, sentence, sentence_similarity(focus_sentence, sentence)))
        print ("Similarity(\"%s\", \"%s\") = %s" % (focus_sentence, sentence, sentence_similarity(focus_sentence, sentence, ignore_integers=True)))

    # print(sentence_similarity(focus_sentence, sentences[2], ignore_integers=True))

if __name__ == '__main__':
    main()
