install.packages(c('repr', 'IRdisplay', 'IRkernel'), type = 'source')
IRkernel::installspec(user = FALSE)
package_list <- read.csv(file = './package_listup.csv')[, 2]
install.packages(package_list)
