from rag_with_trpg.chunk.fixed import fixed_chunking
from rag_with_trpg.config import load_config


def main():
    load_config()
    print(fixed_chunking("abcdefghijklm", 10, 8, 5, doc_id="test"))
    print(fixed_chunking("ab", 3, 2, 3, doc_id="test"))


# 10 | 4 | 2 | 3 | 2
# 0, 0, 2, 4
#
# 0:4
# 2:6
# 4:8
# 6:10
# 8:12 > 8:10 > 7:10 # f: stop
# 9:13 > 9:10 > 6:10
# 8:12 > # inf: non stop


if __name__ == "__main__":
    main()
