wget -r -l1 -nd -A 'enwiki-latest-pages-articles[0-9]*.xml-p*.bz2' \
  --reject '*multistream*' \
  https://dumps.wikimedia.org/enwiki/latest/
