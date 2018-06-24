import subprocess
import sys
import os
import csv
from ConfigParser import SafeConfigParser
from optparse import OptionParser
from listaAlbero_app import listaAlbero,nomeStringA
from listaVirtual import listaAlbero as listaVirtual,nomeStringV


class OID(object):
    def __init__(self):
        """
        costruttore
        @param: file di configurazione
        """
        self.listaOID = []      #salvo il risultato del subprocess
        self.normOID = {}       #dict di oid normalizzate prese con nnsnmpwalk
        self.daFileOID = {}     #dict di oid presi dal file di appoggio
        self.changeOID = {}     #dict di appoggio usata per sovrascrivere il file	
        self.oid = []		#lista di oid da controllare
        self.fqdn = []		#lista di fqdn da controllare

        self.mib_generale = '.1.3.6.1.4.1.9999.9999.200'
        self.mib_descrizione = '.1.3.6.1.4.1.9999.9999.200.1'
        self.mib_indice	 = '.1.3.6.1.4.1.9999.9999.200.2'
        self.mib_valore  = '.1.3.6.1.4.1.9999.9999.200.3'
        self.mib_soglia  = '.1.3.6.1.4.1.9999.9999.200.4'
        self.mib_stato 	 = '.1.3.6.1.4.1.9999.9999.200.5'
        self.mib_voce 	 = '.1.3.6.1.4.1.9999.9999.200.6'
        self.mib_testo	 = '.1.3.6.1.4.1.9999.9999.200.7'

        self.valoreSoglia = ''   #usata per il messaggio dello stato di uscita
        self.confronto = ['INTEGER','Unsigned32',]  #usata per normalizzare le mib con valore intero
        self.listaAlbero = listaAlbero
        self.listaVirtual = listaVirtual
        self.nomeStringA = nomeStringA
        self.nomeStringV = nomeStringV

    def setConf(self,configFile):
        """
        legge il file di configurazione

            [GENERAL]
            OID=
            FQDN=
            SOGLIA=
            TMP_FILE=

        @param: nome file di configurazione
        """
        config = SafeConfigParser()
        config.read(configFile)

        #self.oid = config.get('GENERAL','OID')
        self.oid = self.checkMultiLIST(config.get('GENERAL','OID'))
        self.fqdn = config.get('GENERAL','FQDN')
        self.name = config.get('GENERAL','NAME')
        self.warning = config.get('GENERAL','WARNING')
        self.critical = config.get('GENERAL','CRITICAL')
        self.tmp_file = config.get('GENERAL','TMP_FILE')
        self.limite = config.get('GENERAL', 'LIMITE')
        self.voce = config.get('GENERAL', 'VOCE')
        self.testo = config.get('GENERAL', 'TESTO')

        if config.has_option('GENERAL','CUSTOM'):
            self.custom = config.get('GENERAL','CUSTOM')
        else:
            self.custom = ''

        """
        if config.has_option('GENERAL','CALCOLO'):
            self.calcolo = config.getboolean('GENERAL','CALCOLO')
        else:
            self.calcolo = False

        if config.has_option('GENERAL','ALBERO'):
            self.albero = config.getboolean('GENERAL','ALBERO')
        else:
            self.albero = False

        if config.has_option('GENERAL','VIRTUAL'):
            self.virtual = config.getboolean('GENERAL','VIRTUAL')
        else:
            self.virtual = False
        """

    def getOID(self):
        """
        ottine il valore della oid
        """
        try:
            for oid in self.oid:
                r = subprocess.Popen(['nnmsnmpwalk.ovpl',self.fqdn,oid], stdout=subprocess.PIPE)
                out = r.stdout.read()
                listaOID = out.split('\n')
                for l in listaOID:
                    self.listaOID.append(l)
                    #print(self.listaOID)
        except Exception as e:
            print("errore su nnmsnmpwalk.ovpl   --- {0}".format(e))

    def checkMultiLIST(self,l,c=','):
        """
        prende una stringa e la divinde dentro una lista
        @param l = stringa
        @param c = carattere speciale
        @return LIST
        """
        RES = []
        if l.find(','):
            l = l.split(',')
            for ll in l :
                RES.append(ll)
        else:
            RES.append(l)

        return RES

    ######## START SEND NNM ########
    def controlloSoglia(self,valore):
        """
            ########################################
            ####    controllare le varie soglie ####
            ########################################
            INVIO SOLO AL CAMBIO DI STATO
            RESET E ADD
            RES = 0 -- NORMAL
            RES = 1 -- WARNING
            RES = 2 -- CRITICAL
            RES = 3 -- UNKNOWN (testo)

        al cambio di stato viene inviato un valore di reset ed in seguito il nuovo stato
        @param valore = valore da controllare se in soglia oppure no
        @return : codici di soglia impostati
        """
        try:
            RES = ''
            #print(self.limite)
            v = valore.upper().strip()
            #print("RES = {}".format(v))
            if v.find('OK') != -1:
                #print('ok')
                RES = 0
            elif v.find('WARN') != -1:
                #print("War")
                RES = 1
            elif v.find('CRIT') != -1:
                #print("crit")
                RES = 2
            else:
                #print("int")
                if int(self.limite) == 1:    #limite superiore
                    if int(valore) < int(self.warning):
                        RES = 0
                    elif int(valore) >= int(self.warning) and int(valore) < int(self.critical):
                        RES = 1
                    elif int(valore) >= int(self.critical):
                        RES = 2
                    else :
                        RES = 3
                elif int(self.limite) == 0: #valore inferiore
                    if int(valore) < int(self.critical):
                        RES = 2
                    elif int(valore) >= int(self.critical) and int(valore) <= int(self.warning):
                        RES = 1
                    elif int(valore) > int(self.warning) :
                        RES = 0
                    else :
                        RES = 3
                else:
                    RES = 3
            #IF_RES=RES
            #print("CONTROLLO SOGLIA valore={} limite={} RES={} WAR={} CRI={}".format(int(valore), self.limite,int(RES),int(self.warning),int(self.critical)))
            self.valoreSoglia = RES
            return int(RES)
        except  ValueError as e:
            RES = 3
            return int(RES)

    def sendResetTrap(self,indice_oid,valore,stato_rilevato):
        """
        metodo per il reset della trap
        """
        self.sendUpdateTrap(indice_oid,valore,stato_rilevato)

    def sendUpdateTrap(self,indice_oid,valore,stato_rilevato):
        """
        metodo generico di invio trap di aggiornamento
        fqdn = 		cdm-wf-lb01.ac.bankit.it
        generale =      .1.3.6.1.4.1.9999.9999.200
        descrizione = 	.1.3.6.1.4.1.9999.9999.200.1=sysChassisFanSpeed.3
        index =		.1.3.6.1.4.1.9999.9999.200.2=3
        value = 	.1.3.6.1.4.1.9999.9999.200.3=7142
        soglia = 	.1.3.6.1.4.1.9999.9999.200.4=4
        stato = 	.1.3.6.1.4.1.9999.9999.200.5=Normal
        voce  = 	.1.3.6.1.4.1.9999.9999.200.6=Voce
        testo  = 	.1.3.6.1.4.1.9999.9999.200.7=Testo
        """
        desc = self.mib_descrizione +' octetstring "'+ str(indice_oid).strip()+'"'
        index = self.mib_indice
        stato = '""'
        if 'Load Balancing Pool' in str(indice_oid):
            s = str(valore).split('-')
            stato = self.mib_stato + ' octetstring "' + str(s[0]).strip()+'"'
        else:
            index = self.mib_indice + ' octetstring "' + str(self.findIndex(indice_oid)).strip()+'"'
            stato = self.mib_stato + ' octetstring "' + str(self.findStato(stato_rilevato)).strip()+'"'

        #index = self.mib_indice + ' octetstring "' + str(self.findIndex(indice_oid)).strip()+'"'
        #stato = self.mib_stato + ' octetstring "' + str(self.findStato(stato_rilevato)).strip()+'"'

        value = self.mib_valore + ' octetstring "' + str(valore).strip()+'"'
        soglia = self.mib_soglia + ' octetstring "' + str(self.findValoreSoglia()).strip()+'"'
        voce = self.mib_voce + ' octetstring "' + str(self.voce).strip()+'"'
        #testo = self.mib_testo + ' octetstring "' +str(self.testo).strip()+' '+str(valore)+' (threshold '+str(self.findValoreSoglia()).strip()+')"'
        testo = self.mib_testo + ' octetstring "' + self.findTesto(valore) + '"'

        CMD = '/opt/OV/bin/nnmsnmpnotify.ovpl -v 2c "" -a {} {} {} {} {} {} {} {} {}'.format(self.fqdn, self.mib_generale, desc, index, value, soglia, stato, voce, testo)
        print CMD
        #r = subprocess.Popen([CMD],shell=True )# stdout=subprocess.PIPE,)
        #print r
    
    def findValoreSoglia(self):
        """
        trova la soglia da prendere in cosiderazione
        @return : ritorna il valore della soglia warning o critical da prendere in cosiderazione
        """
        ris = ''
        if self.valoreSoglia <= 1 :
            ris = self.warning
        elif self.valoreSoglia == 2 :
            ris = self.critical
        else :
            pass

        return ris

    def findIndex(self,key):
        """
        trova l'indice per la trap di uscita 	sysChassisTempTemperature.6
        @param key: chiave contenente l'indice
        @return : valore numerico dell 'indice
        """
        #print key
        index = key.split('.')
        return index[1]

    def findStato(self,valore_rilevato):
        """
        trova lo stato dell'errore
        0 = NORMAL
        1 = WARNING
        2 = CRITICAL
        3 = UNKNOWN
        @return : tipo di stato
        """
        ris = ''
        #if self.valoreSoglia == 0 :
        print valore_rilevato
        if valore_rilevato == 0 :
            ris = 'Normal'
        #elif self.valoreSoglia == 1:
        elif valore_rilevato == 1:
            ris = 'Warning'
        #elif self.valoreSoglia == 2:
        elif valore_rilevato == 2:
            ris = 'Critical'
        else :
            ris = 'UNKNOWN'
        return ris

    def findTesto(self,valore):
        #TESTO=Fan Speed is at %%VALORE%% (threshold %%FINDVALORESOGLIA%%)
        #str(valore)
        #str(self.findValoreSoglia())
        app = self.testo.replace('__VALORE__', str(valore))
        app = app.replace('__FINDVALORESOGLIA__', self.findValoreSoglia().strip())
        return app

    def sendListaNNM(self,nnM):
        """
        metodo di appoggio per l'invio delle trap, da una lista-di-liste estrae i valori da inviare
        @param nnM: list-of-list
        """
        for n in nnM:
            #print n
            if len(n) == 3:
                self.sendNNM(n[0],n[1],n[2])
            else:
                self.sendNNM(n[0],n[1])

    def sendNNM(self,indice_oid,valore,oldValore=False):
        """
        """
        #print oldValore
        if not oldValore :							#condizione 1
            status = self.controlloSoglia(valore)
            #oldValore='OOOLLLDDD'
            #print indice_oid
            #print valore
            self.sendUpdateTrap(indice_oid,valore,oldValore)
        elif valore == oldValore :					#condizione 2
            pass
        else :
            oldStatus = self.controlloSoglia(oldValore)
            newStatus = self.controlloSoglia(valore)

            #print('{} {}'.format(oldStatus,newStatus))				#condizione 3
            if oldStatus != newStatus:		 				#condizione 3.1
                self.sendResetTrap(indice_oid,oldValore,oldStatus)
                self.sendUpdateTrap(indice_oid,valore,newStatus)

            elif oldStatus == 3 and newStatus == 3:			#sono nella condizione di avere una mib di carattere descrittivo
                self.sendResetTrap(indice_oid,oldValore,oldStatus)
                self.sendUpdateTrap(indice_oid,valore,newStatus)
            else:							#condzione 3.2
                #print("non invio nulla")
                pass

    ######## END SEND NNM ########

    ####### START NORMALIZZA OID #######
    def normalOID(self):
        """
        normalizza la oid presa da nnmsnmpnotify.ovpl
        """
        for l in self.listaOID:
            if 'Index' not in l:
                if len(l) !=0:
                    if l.find(self.name) > 0:
                        s=l.split(self.name)
                        l=s[1].split(':')
                        ll=s[1]
                        value=ll[ll.index(':')+1:]
                        #self.normOID[l[0][1:]]=l[len(l)-1]
                        self.normOID[l[0][1:]]=self.normalVALUE(value)
                    else:
                        ll = l
                        l=l.split(':')
                        value=ll[ll.index(':')+1:]
                        #self.normOID[l[0]]=l[len(l)-1]
                        self.normOID[l[0]]=self.normalVALUE(value)

    def normalVALUE(self,value):
        """
        converte in valori numerici le stringe che contengono INTEGER, Unsigned32
        """
        res = value
        for f in self.confronto:
            if value.find(f) >= 0 :
                r = value.split(':')
                res = r[1]
        return res

    ####### END NORMALIZZA OID #######

    def checkDiff(self):
        """
        controlla nel file di tmp il vecchio valore
        {'sysChassisTempTemperature.1 ':' 25'}

                ####	AGGIUNGERE FQDN   ####

        """
        nnM=[]  # indice_oid,valore,oldValore=False)   --- DA AGGIUNGERE FQDN

        writeF=False
        sendTrap=False
        if os.path.isfile(self.tmp_file):
            #print("il file esiste")
            #se il file esiste eseguo l'import
            f = open(self.tmp_file,'r')
            for line in f:
                l=line.replace("\n","")
                l=l.split(';')
                self.daFileOID[l[0]]=l[1]
            f.close()
            for k,v in self.normOID.iteritems():
                if self.daFileOID.has_key(k):   # la chiave e' presente sul file di appoggio
                                                        # confronto i valori
                    #print 'k'+k+'-F-'+self.daFileOID[k]+'-N-'+self.normOID[k]+'-'
                    if self.daFileOID[k] != self.normOID[k]:        # i valori sono differenti
                        #print 'k'+k+'-F-'+self.daFileOID[k]+'-N-'+self.normOID[k]+'-'
                        # aggiounogo k v su un dict di appoggio presa da normOID
                        self.changeOIDFile(k,v)
                        nnM.append([k,v,self.daFileOID[k]])  #k k chiave, v valore nuovo, self.daFileOID valore vecchio
                        #print nnM
                        #self.sendNNM(k,v,self.daFileOID[k])
                        writeF=True

                    else :  # i valori sono uguali, li aggiungo alla dict per costruire il file
                        # aggiungo k v su un dict di appoggio presa da normOID
                        self.changeOIDFile(k,v)

                else:   # la chiave non risulta sul file di appoggio
                    # aggiounogo k v su un dict di appoggio presa da normOID
                    #print '#'+str(self.daFileOID[k])+'#'+str(self.normOID[k])+'#'
                    self.changeOIDFile(k,v)
                    nnM.append([k,v])
                    self.sendNNM(k,v)
                    writeF=True

            if writeF:
                self.writeFile(self.changeOID)
                self.sendListaNNM(nnM)
                #print("eseguo l'update del file")
            #else:
                #print("nessun cambiamento da apportare")

        else:
            ######################
            # IL FILE NON ESISTE #
            #####################
            #print("scrivo il file")
            self.writeFile(self.normOID)  #scrivo sul file per vedere le differenze con il prossimo controllo
            #for k,v in self.normOID.iteritems():
                #self.sendNNM(k,v)

    def changeOIDFile(self,k,v):
        """
        crea un dict che sovrascrive i file creato in precedenza
        @param k: oid
        @param v: value
        """
        self.changeOID[k]=v

    ####### START CUSTOM ATTRIBUTE ##########
    def memoriUsata(self):
        """
        esegue due entry e calcola la memoria utilizzata
        """
        hrStorageSize = {}
        hrStorageUsed = {}
        percento={}
        for k,v in self.normOID.iteritems():
            #print k
            l= k.split('.')
            #print l
            if l[0].find('hrStorageSize') >= 0:
                hrStorageSize[l[1]] = v
            elif l[0].find('hrStorageUsed') >= 0:
                hrStorageUsed[l[1]] = v
            else:
                pass

        for index_used,value_used in hrStorageUsed.iteritems():
            c = (float(value_used) / float(hrStorageSize[index_used])) * 100
            newKey = "hrStorage."+str(index_used)
            #percento[newKey] = str(int(c))+" %"
            percento[newKey] = str(int(c))

        #for	 k,v in percento.iteritems():
            #print k, v

        self.normOID = percento
    
    def associazioneOID(self,listaCommon,nomeString):
        """
        """
        mib = ''
        lista = {}
        for k,v in self.normOID.iteritems():
            #for la in self.listaAlbero:    #parte 1
            for la in listaCommon:    #parte 1
                if la in v:
                    for oid in self.oid:
                        if oid in k:
                            oid = k.split(oid)
                            mib = oid[1][1:]   #trovo la mib da confrontare con altre
                            mib=mib.strip()
                            key,value=self.associazioneOID_NUM(mib,la,nomeString)
                            lista[key]=value

        return lista   #dict
 
    def associazioneOID_NUM(self, mib, nomeAlbero, nomeString):
        """
        in base alla mib trovata effettuo l'associazione
        @param mib:
        @return : key,value
        """
        key=''
        value=''
        contatore = 0
        OK_ = 0
        ERR_ = 0
        NOMI_NODO = ''
        for k,v in self.normOID.iteritems():
            if mib in k :
                if not('STRING' in v):
                    contatore = contatore + 1
                    if int(v) < 5 :
                        OK_ = OK_ + 1
                    else:
                        ERR_ = ERR_ + 1
                else:
                    if not(nomeAlbero in v):
                        app = v.split(':')
                        NOMI_NODO = NOMI_NODO + app[1]+','

        #key = self.nomeString + ' ' +nomeAlbero
        key = nomeString + ' ' +nomeAlbero

        if OK_ > 0 and ERR_ <= 0 :
            value = "OK - {} of {} members are up".format(OK_,contatore)
        else:
            value = "CRIT - {} of {} members are up, down/disabled nodes {}".format(OK_,contatore,OK_,NOMI_NODO)

        return 	key,value

    def virtualServer(self,listaVirtual,nomeStringV):
        """
        @param listaVirtual
        @param nomeStringV
        """
        listaErr={0:'none', 1:'green', 2:'yellow', 3:'red', 4:'blue', 5:'gray'}
        key = ''
        value = ''
        contatore = 0
        OK_ = 0
        ERR_ = 0
        NOMI_NODO = ''
        pass

    def chassisFan(self):
        statoD={1:'Ok', 2:'Warning', 3:'Critical'}
        appS={}
        appF={}
        for k,v in self.normOID.iteritems():
            if k.find("sysChassisFanStatus") != -1:
                k = k.split('.')
                appS[k[1]] = v
            elif k.find("sysChassisFanSpeed") != -1:
                k = k.split('.')
                appF[k[1]] = v

        msg = 'Fan Processor'

    ####### END CUSTOM ATTRIBUTE ##########

    def run(self):
        """
        esegue il controllo assegnato
        """
        #self.getOID()
        #self.normalOID()
        #self.toCSV()
        self.fromCSV()
        """
        if self.calcolo:
            self.memoriUsata()

        if self.albero:
            self.normOID=self.associazioneOID(self.listaAlbero,self.nomeStringA)

        if self.virtual:
            #self.normOID=self.associazioneOID(self.listaVirtual,self.nomeStringV)
            self.virtualServer(self.listaVirtual,self.nomeStringV)
        """
        self.customLauncher(self.custom)
        self.checkDiff()
        for k,v in self.normOID.iteritems():
                print(k,v)

    def customLauncher(self,custom=None):
        """
        """
        if custom.upper().strip() == 'ALBERO':
            self.normOID = self.associazioneOID(self.listaAlbero, self.nomeStringA)
        elif custom.upper().strip() == 'VIRTUAL':
            self.virtualServer(self.listaVirtual, self.nomeStringV)
        elif custom.upper().strip() == 'MEMORIA':
            self.memoriUsata()
        elif custom.upper().strip() == 'FAN':
            pass
        else:
            pass

    def writeFile(self,normOID):
        """
        scritture sul file
        @param: normOID
        fqdn; oid ;valore
        [ { 'FQDN': fqdn, 'OID': oid, 'VALUE':value}, ]
        """
        f=open(self.tmp_file,'w')
        for k,v in normOID.iteritems():
            f.write(k+";"+v+"\n")
        f.close()

    def toCSV(self):
        """
        create csv to dict
        """
        fileName="dirname.csv"
        with open(fileName,'wb') as f:
            w = csv.DictWriter(f, self.normOID.keys())
            w.writeheader()
            w.writerow(self.normOID)

    def fromCSV(self,fileName='dirname.csv'):
        reader = csv.DictReader(open(fileName, 'rb'))
        dict_list = []
        for line in reader:
            dict_list.append(line)
            #print("{} len".format(len(line)))

        for k,v in dict_list[0].iteritems():
            self.normOID[k]=v

if __name__ == '__main__':
    """
    example ./f5-plugin.py -f FILECONF
    """
    if sys.argv > 1:
        fileConf = sys.argv[1]

        oid = OID()
        oid.setConf(fileConf)
        oid.run()
    else :
        print("ERRORE parametri di avvio mancanti")