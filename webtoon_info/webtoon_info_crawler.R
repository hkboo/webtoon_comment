library(xml2)
library(XML)
library(stringr)
library(dplyr)

url <- "https://comic.naver.com/webtoon/weekday"
html <- read_html(url)
html.parsed <- htmlParse(html)

base.path <- "//div[@class='list_area daily_all']//div[@class='col_inner']/ul/li/a"
webtoon_urls <- xpathSApply(html.parsed, base.path, xmlGetAttr, "href")

names.base.path <- paste(base.path, "text()", sep='/')
webtoon_names <- xpathSApply(html.parsed, names.base.path, xmlValue)

df <- data.frame(list("url"=webtoon_urls, "name"=webtoon_names))
df$dayname <- str_sub(df$url, -3, -1)

tmp_title_id <- str_extract_all(df$url, "titleId=[0-9]*")
df$title_id <- as.integer(unlist(str_remove_all(tmp_title_id, "titleId=")))

df$full_url <- paste0("https://comic.naver.com", df$url)
df$idx <- seq(0, nrow(df)-1)

df <- df[c(6, 2, 3, 4, 1, 5)]

#### 웹툰 소개 정보
get_webtoon_desc <- function(url) {
  html <- read_html(url)
  html.parsed <- htmlParse(html)

  base.path <- "//div[@class='detail']/h2/span[@class='wrt_nm']"
  artist <- xpathSApply(html.parsed, base.path, xmlValue, trim=T)
  
  base.path <- "//div[@class='detail']/p/text()"
  desc <- xpathSApply(html.parsed, base.path, xmlValue, trim=T)
  desc <- paste(desc, collapse = ' ')

  base.path <- "//div[@class='detail']/p[@class='detail_info']/span[@class='genre']"
  genre <- xpathSApply(html.parsed, base.path, xmlValue, trim=T)

  base.path <- "//div[@class='detail']/p[@class='detail_info']/span[@class='age']"
  age <- xpathSApply(html.parsed, base.path, xmlValue, trim=T)

  return(c(artist, desc, genre, age))
}


desc.mat <- lapply(lapply(df$full_url, get_webtoon_desc), rbind)
new_df <- data.frame()
for (i in 1:length(desc.mat)) {
  new_df <- rbind(new_df, as.data.frame(desc.mat[i]))
}

names(new_df) <- c("artist", "desc", "genre", "age")


### 웹툰 정보 데이터 저장
final_df <- cbind(df, new_df)
write.table(final_df, "./webtoon_info.tsv", sep="\t", row.names = F)