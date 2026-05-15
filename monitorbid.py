import requests
import re
import time
import os
import json
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

class BidooAuctionBot:
    def __init__(self, auction_id):
        self.id_asta = auction_id
        self.session = requests.Session()
        self.participants = {}  
        self.vincitore_finale = None
        self.puntate_vincitore = 0
        self.running = True    
        self.last_vincitore = None
        self.last_prezzo = None
        self.json_file = f"{self.id_asta}.json"
        self.history_file = f"{self.id_asta}_history.json"
        self.init_json_files()
    
    def init_json_files(self):
        initial_data = {
            "auction_id": self.id_asta,
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "status": "active",
            "winner": None,
            "total_bids": 0,
            "total_participants": 0,
            "participants": {},
            "participants_list": []
        }
        
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
        
        initial_history = {
            "auction_id": self.id_asta,
            "start_time": datetime.now().isoformat(),
            "total_bids": 0,
            "history": []
        }
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(initial_history, f, indent=2, ensure_ascii=False)
    
    def save_to_json(self):
        data = {
            "auction_id": self.id_asta,
            "start_time": self.start_time if hasattr(self, 'start_time') else datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "status": "terminated" if self.vincitore_finale else "active",
            "winner": self.vincitore_finale,
            "winner_bids": self.puntate_vincitore if self.vincitore_finale else None,
            "total_bids": sum(self.participants.values()),
            "total_participants": len(self.participants),
            "participants": self.participants,
            "participants_list": [
                {"username": k, "bids": v, "rank": i+1} 
                for i, (k, v) in enumerate(sorted(self.participants.items(), key=lambda x: x[1], reverse=True))
            ]
        }
        
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def save_bid_to_history(self, vincitore, prezzo, puntata_numero):
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            history_data = {
                "auction_id": self.id_asta,
                "start_time": datetime.now().isoformat(),
                "total_bids": 0,
                "history": []
            }
        
        bid_entry = {
            "timestamp": datetime.now().isoformat(),
            "time": datetime.now().strftime('%H:%M:%S'),
            "winner": vincitore,
            "price": prezzo,
            "bid_number": puntata_numero,
            "total_bids_so_far": sum(self.participants.values())
        }
        
        history_data["history"].append(bid_entry)
        history_data["total_bids"] = len(history_data["history"])
        history_data["last_update"] = datetime.now().isoformat()
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
    
    def get_auction_info(self):
        try:
            info_asta = f"https://it.bidoo.com/data.php?ALL={self.id_asta}&LISTID=0"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
                "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
                "Accept-Encoding": "gzip, deflate",
                'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0'
            }
            
            response = self.session.get(info_asta, headers=headers, timeout=10)
            data = response.text
            
            if ';OFF;' in data:
                parts = data.split(';')
                if len(parts) > 4:
                    self.vincitore_finale = parts[4]
                    if self.vincitore_finale in self.participants:
                        self.puntate_vincitore = self.participants[self.vincitore_finale]
                    self.save_to_json() 
                    return {'status': 'ended', 'vincitore': self.vincitore_finale}
            
            if ';STOP;' in data:
                print(f"{Fore.YELLOW}⏸ Asta in pausa...{Style.RESET_ALL}")
                return {'status': 'paused'}
            
            if ';' in data:
                parts = data.split(';')
                if len(parts) >= 5:
                    prezzo = str(int(parts[3]) / 100) + '€'
                    prezzo_raw = int(parts[3])
                    vincitore = parts[4]
                    
                    if vincitore and (vincitore != self.last_vincitore or prezzo_raw != self.last_prezzo):
                        if vincitore not in self.participants:
                            self.participants[vincitore] = 0
                        self.participants[vincitore] += 1
                        self.last_vincitore = vincitore
                        self.last_prezzo = prezzo_raw
                        self.save_bid_to_history(vincitore, prezzo, self.participants[vincitore])
                        self.save_to_json()
                        
                        return {
                            'status': 'active',
                            'vincitore': vincitore,
                            'prezzo': prezzo,
                            'puntate': self.participants[vincitore],
                            'is_new': True
                        }
                    else:
                        return {
                            'status': 'active',
                            'vincitore': vincitore,
                            'prezzo': prezzo,
                            'puntate': self.participants.get(vincitore, 0),
                            'is_new': False
                        }
            
            return {'status': 'no_data'}
            
        except Exception as e:
            error_msg = f"Errore nel recupero dati: {str(e)}"
            print(f"{Fore.RED}❌ {error_msg}{Style.RESET_ALL}")
            return {'status': 'error', 'error': str(e)}
    
    def clear_console(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        header = f"""
{Fore.CYAN}8b    d8  dP"Yb  88b 88 88 888888  dP"Yb  88""Yb 
88b  d88 dP   Yb 88Yb88 88   88   dP   Yb 88__dP 
88YbdP88 Yb   dP 88 Y88 88   88   Yb   dP 88"Yb  
88 YY 88  YbodP  88  Y8 88   88    YbodP  88  Yb{Style.RESET_ALL}

{Fore.GREEN}88""Yb 88 8888b.      Yb    dP   .d 
88__dP 88  8I  Yb      Yb  dP  .d88 
88""Yb 88  8I  dY       YbdP     88 
88oodP 88 8888Y"         YP      88 {Style.RESET_ALL}

{Fore.YELLOW}{'='*60}
{Style.RESET_ALL}"""
        print(header)
    
    def display_auction_table(self):
        print(f"{Fore.CYAN}Asta ID: {self.id_asta}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Ultimo aggiornamento: {datetime.now().strftime('%H:%M:%S')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💾 Dati salvati in: {self.json_file}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📜 Cronologia in: {self.history_file}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{'Utente':<20} {'Puntate usate':<15}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{'-'*35}{Style.RESET_ALL}")
        
        sorted_participants = sorted(self.participants.items(), key=lambda x: x[1], reverse=True)
        
        for username, puntate in sorted_participants:
            if self.vincitore_finale and username == self.vincitore_finale:
                print(f"{Fore.RED}{username:<20} {puntate:<15}{Style.RESET_ALL}")
            elif puntate > 100:
                print(f"{Fore.YELLOW}{username:<20} {puntate:<15}{Style.RESET_ALL}")
            else:
                print(f"{username:<20} {puntate:<15}")
        
        print(f"{Fore.WHITE}{'-'*35}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Totale partecipanti: {len(self.participants)}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Totale puntate: {sum(self.participants.values())}{Style.RESET_ALL}")
        
        if self.vincitore_finale:
            print(f"\n{Fore.RED}{'='*50}")
            print(f"🏆 ASTA TERMINATA! 🏆")
            print(f"Vincitore: {self.vincitore_finale}")
            print(f"Puntate usate: {self.puntate_vincitore}")
            print(f"{'='*50}{Style.RESET_ALL}")
    
    def run(self):
        self.clear_console()
        self.print_header()
        
        print(f"{Fore.GREEN}🔍 Monitoraggio asta {self.id_asta} in corso...")
        print(f"{Fore.CYAN}Premi Ctrl+C per terminare{Style.RESET_ALL}\n")
        
        error_count = 0
        
        while self.running:
            try:
                result = self.get_auction_info()
                
                if result['status'] == 'ended':
                    self.clear_console()
                    self.print_header()
                    self.display_auction_table()
                    print(f"\n{Fore.GREEN}✅ Asta terminata! Dati salvati in JSON{Style.RESET_ALL}")
                    time.sleep(5)
                    
                elif result['status'] == 'active':
                    if result.get('is_new', False):
                        self.clear_console()
                        self.print_header()
                        self.display_auction_table()
                        print(f"{Fore.GREEN}✨ Nuova puntata! {result['vincitore']} - {result['prezzo']} (Puntata #{result['puntate']}){Style.RESET_ALL}")
                        error_count = 0
                
                elif result['status'] == 'paused':
                    # Asta in pausa
                    pass
                
                elif result['status'] == 'error':
                    error_count += 1
                    if error_count > 5:
                        time.sleep(30)
                        error_count = 0
                
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}👋 Terminazione...{Style.RESET_ALL}")
                self.save_to_json()
                print(f"{Fore.GREEN}✅ Dati salvati in {self.json_file}{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"{Fore.RED}❌ Errore: {str(e)}{Style.RESET_ALL}")
                time.sleep(5)

def main():
    while True:
        try:
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            auction_id = input(f"{Fore.YELLOW}📊 Inserisci ID asta: {Style.RESET_ALL}").strip()
            
            if not auction_id:
                print(f"{Fore.RED}❌ ID non valido.{Style.RESET_ALL}")
                continue
            
            bot = BidooAuctionBot(auction_id)
            bot.run()
            
            risposta = input(f"\n{Fore.YELLOW}Monitorare altra asta? (s/n): {Style.RESET_ALL}").strip().lower()
            if risposta != 's':
                print(f"{Fore.GREEN}👋 Arrivederci!{Style.RESET_ALL}")
                break
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Uscita...{Style.RESET_ALL}")
            break

if __name__ == "__main__":
    try:
        import colorama
    except ImportError:
        os.system('pip install colorama')
        import colorama
    
    main()
