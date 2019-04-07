from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import requests,time,re,random,MySQLdb
from bs4 import BeautifulSoup
from requests.packages.urllib3.exceptions import InsecureRequestWarning     #强制取消警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)      #强制取消警告

class xuanwu():
	def __init__(self):
		self.user_agent_list = ["Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36",
                    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)",
                    "Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10.5; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36"]
		self.agent_url = 'https://ip.seofangfa.com/'
		self.agent_ip_list = []
		self.headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36'}
		self.datas = []

	def spider(self,now_date):
		while str(now_date.strftime('%d')):
			year_month_day = now_date.strftime('%y/%m/%d')
			# year_month_day = '19/02/14'	'17/05/31'	'17/05/24'
			url = 'https://xuanwulab.github.io/cn/secnews/20{0}/index.html'.format(year_month_day)
			if year_month_day == '16/01/01':
				print('已到最早发文日期：{}'.format(year_month_day))
				break
			html = self.request(url)
			html_soup = BeautifulSoup(html.text,'lxml')
			try:
				# mess_list = html_soup.find('ul',attrs={'class','weibolist'}).find_all('p')	# 另一个ul的拿不到
				mess_list = html_soup.find('div',attrs={'id':'weibowrapper'}).find_all('p')		# 这里之所以可以用p时因为目标div下只有一个p,而parse_second的div下有2个,有一个p不是目标
				# 因为17/05/31的特殊，所以在想第二种匹配，tag拿singleweibotext下的i标签的内容，标题和链接拿translated下的p的text和p的a[href]
				# mess_list = html_soup.find('div',attrs={'id':'weibowrapper'}).find_all('div',attrs={'class':'singleweibotext'})
			except:
				print(year_month_day,'404')
			else:
				if len(mess_list) == 0:
					print(year_month_day,'无文章')
				else:
					print(year_month_day,'有文章')
					self.parse_first(html_soup,year_month_day,mess_list)		# year_month_day,mess_list 传入用于插入数据

			check_date = now_date.strftime('%y/%m') + '%'
			old_m = now_date.strftime('%m')	# 当前日期的月份
			now_date += timedelta(days = -1)
			new_m = now_date.strftime('%m')	# 下一个日期的月份

			if old_m != new_m:			# 判断是否相同一个月份
				if self.datas == []:
					print('\n空数据\n')
				else:
					self.database_insert(old_m,check_date)	# 比对月份

	def parse_first(self,html_soup,year_month_day,mess_list):		# 解析第一种页面
		try:
			mess_list[0].span.get_text().replace('[','').replace(']','').strip()
		except:
			print('使用二次解析...')
			self.parse_second(html_soup,year_month_day)		# 解析第二种页面
		else:
			for mess in mess_list:
				regular1 = r"(?<=</span>).+?(?=<a)"	# 正则匹配规则
				pattern = re.compile(regular1)		# 编译正则表达式
				matcher = re.search(pattern,str(mess))
				tag = mess.span.get_text().replace('[','').replace(']','').strip()
				
				data = self.filter_none(year_month_day,tag,matcher,mess)	# 构成插入数据库元组的4个属性
				if data == False:
					pass
				else:
					self.datas.append(data)

	def parse_second(self,html_soup,year_month_day):			# 解析第二种页面
		# 匹配第一个ul
		first_ul_list = html_soup.find('ul',attrs={'class':'weibolist'}).find_all('p')[1::3]
		for first_ul in first_ul_list:
			ul = str(first_ul).replace('\n','')
			regular1 = r'(?<=</i>]).+?(?=<a)'	# 正则匹配规则
			pattern = re.compile(regular1)		# 编译正则表达式
			matcher = re.search(pattern,ul)
			tag = first_ul.i.get_text().replace('[','').replace(']','').strip()

			data = self.filter_none(year_month_day,tag,matcher,first_ul)	# 构成插入数据库元组的4个属性
			if data == False:
				pass
			else:
				self.datas.append(data)		
		# 匹配第二个ul
		second_ul_list = html_soup.find('ul',attrs={'id':'manualfeedlist'}).find_all('p')[1::2]	# 第一个是rss,第二个是目标，第三个是rss,第四个目标
		for second_ul in second_ul_list:
			ul = str(second_ul).replace('\n','')
			regular1 = r'(?<=</i>]).+?(?=<a)'	# 正则匹配规则
			pattern = re.compile(regular1)		# 编译正则表达式
			matcher = re.search(pattern,ul)
			tag = second_ul.i.get_text().replace('[','').replace(']','').strip()
			
			data = self.filter_none(year_month_day,tag,matcher,second_ul)	# 构成插入数据库元组的4个属性
			if data == False:
				pass
			else:
				self.datas.append(data)
	
	def filter_none(self,year_month_day,tag,matcher,mess):
		try:
			title = matcher.group().strip()
		except:
			title = 'None'
		try:
			link = mess.a['href']
		except:
			link = 'None'
		if (title == 'None') & (link == 'None'):		# 过滤None内容
			return False
		else:
			return (year_month_day,tag,title,link)

	def database_insert(self,old_m,check_date):
		conn = MySQLdb.connect(host='localhost',port=3306,user='root',passwd='',db='xuanwulab',charset='utf8')
		cur = conn.cursor()		# 连接数据库
		sql = "INSERT INTO test(date,tag,title,link) VALUES(%s,%s,%s,%s)"
		print('\n%s月文章总数为: %s'%(old_m,len(self.datas)))
		isJudge = self.database_check(cur,check_date)	# 插入前判断
		print(isJudge)
		if isJudge == False:
			cur.executemany(sql,self.datas)
			print('插入成功\n')
			test_exec = cur.execute("SELECT * FROM test;")
			test_fet =cur.fetchmany(test_exec)
			self.datas = []
			cur.close()
			conn.commit()
			conn.close()
		else:
			self.datas = []

	def database_check(self,cur,check_date):		# 检查是否有重复
		select_sql  = 'SELECT count(*) FROM test where date like "%s"' % (check_date)	# 查询数据库指定月份的文章数
		select_exec = cur.execute(select_sql)
		select_fet =cur.fetchmany(select_exec)
		count_num = str(select_fet).strip("()',")
		
		total_sql = 'SELECT count(*) FROM test;'										# 查询数据库文章总数
		total_exec = cur.execute(total_sql)
		total_fet =cur.fetchmany(total_exec)

		print('数据库所有文章数量为:',str(total_fet).strip("()',"))
		print('与本月匹配的文章数量为:',count_num)	# 查询指定月份的文章在数据库的数量		
		if count_num == str(len(self.datas)):
			print('数据库中查询已存在！')
			return True
		else:
			print('数据库中查询不到，即将插入...')
			return False

	def request(self,url):
		return requests.get(url=url,headers=self.headers,verify=False,timeout=10)

	def work(self):
		now_date = datetime.now()
		self.spider(now_date)
xuanwu = xuanwu()
xuanwu.work()