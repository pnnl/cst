clear all;
close all;
clc
% probability distribution identification
% by Bowen Huang@PNNL
windSpeedAt140mms = csvread("0_39.97_-128.77_2019.csv",2,7);
pd = fitdist(windSpeedAt140mms,'wbl');
histogram(windSpeedAt140mms,'Normalization','probability')
grid on
xlabel('Wind speed (m/s)')
ylabel('Probability')
hold on

x = 0:.1:35;
pdf_wbl = pdf(pd,x);
plot(x,pdf_wbl,'LineWidth',2)

N = 8760
new_samples = wblrnd(pd.a,pd.b,N,1)
figure
hold on
plot(new_samples)
plot(windSpeedAt140mms)