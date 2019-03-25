'''
nltk.download(['wordnet', 'stopwords', 'punkt']) if not already downloaded.
Should add to wordnet if you want more words to compare as reference to.
'''
from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet as wn


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
    if wn_tag is None:
        return None
    try:
        return wn.synsets(word, wn_tag)[0]
    except:
        return None


def sentence_similarity(sentence1, sentence2):
    """ compute the sentence similarity using Wordnet """
    # Tokenize and tag
    sentence1 = pos_tag(word_tokenize(sentence1))
    sentence2 = pos_tag(word_tokenize(sentence2))

    # Get the synsets for the tagged words
    synsets1 = [tagged_to_synset(*tagged_word) for tagged_word in sentence1]
    synsets2 = [tagged_to_synset(*tagged_word) for tagged_word in sentence2]

    # Filter out the Nones
    synsets1 = [ss for ss in synsets1 if ss]
    synsets2 = [ss for ss in synsets2 if ss]
    #print(synsets1)
    #print(synsets2)
    score, count = 0.0, 0.0

    # For each word in the first sentence
    for synset in synsets1:
        # Get the similarity value of the most similar word in the other sentence

        best_score=[synset.path_similarity(ss) for ss in synsets2 if synset.path_similarity(ss)]

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
            synsets.append(str(synset))
        else:
            synsets.append(tagged_word[0])
    return str(sorted(synsets))

def main():
    # sentences = [
    #     #"Dogs are awesome.",
    #     #"Some gorgeous creatures are felines.",
    #     #"Dolphins are swimming mammals.",
    #     "Dogs are the best people.",
    # ]
    # focus_sentence = "Dogs are coolest animals."
    #
    # for sentence in sentences:
    #     print ("Similarity(\"%s\", \"%s\") = %s" % (focus_sentence, sentence, sentence_similarity(focus_sentence, sentence)))
    #     #print ("Similarity(\"%s\", \"%s\") = %s" % (sentence, focus_sentence, sentence_similarity(sentence, focus_sentence)))
    # memo = {get_tokenized_sentence('Neurons, Brain'): 'myrow'}
    # print(memo)
    get_tokenized_sentence('mouse microRNA')

if __name__ == '__main__':
    main()
