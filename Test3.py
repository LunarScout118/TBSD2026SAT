from random import*
d=sample("A23456789TJQK"*4,52)
def tot(c):
    a=t=0
    for x in c:a+=(x=="A");t+=10+(x=="A")if x in"ATJQK"else int(x)
    while(t>21)*a:t-=10;a-=1
    return t,a>0
dl,sc,fc=lambda t:t[1]*(t[0]==17)or t[0]<17,lambda t:"HSaorfdt  "[t[1]::2]+str(t[0]),"+".join
if(pb:=(pt:=tot(pc:=[d.pop(),d.pop()]))[0]==21)|(db:=(dt:=tot(dc:=[d.pop(),d.pop()]))[0]==21):print(("Push","Player wins","Dealer wins")[pb-db],f"({sc(pt)}/{sc(dt)}).");exit()
print(f"Dealer upcard: {dc[0]}\n\nCurrent score: {sc(pt)} ({fc(pc)}).")
while 1:
    if not(c:=input("\nHit (1) or stand (2)? ").strip()):print("Game forfeited.");break
    elif c=="1":
        pc.append(d.pop());pt=tot(pc)
        if pt[0]>21:print(f"Bust ({sc(pt)}, {fc(pc)})\nDealer wins.");break
        print(f"Current score: {sc(pt)} ({fc(pc)}).")
    elif c=="2":
        print(f"Final score: {sc(pt)} ({fc(pc)}).")
        while dl(dt:=tot(dc)):dc.append(d.pop())
        print(f"Dealer score: {sc(dt)} ({fc(dc)})\n")
        if dt[0]>21:print(f"Dealer bust ({sc(dt)}).\nPlayer wins.");break
        print(((pt[0]!=dt[0])*f"{'DPelaalyeerr'[pt[0]>dt[0]::2]} wins"or"Push"),f"({sc(pt)}/{sc(dt)}).");break
    else:print("Please provide a valid input.")