.PHONY: orbstack-test
orbstack-test:
	orbctl create -p ubuntu:focal dshield
	orb -m dshield -u root adduser dshield
	orb -m dshield -u root bash -c "apt update && apt install -y git openssh-server && apt -y upgrade"
	orbctl restart dshield
	orb -m dshield -u dshield bash -c 'git clone https://github.com/yaleman/dshield.git /home/dshield/dshield'
	orb -m dshield -u root bash -c 'cd /home/dshield/dshield && /home/dshield/dshield/bin/install.sh'
	orbctl restart dshield
