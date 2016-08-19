// Task : Handling js functions for cull UI app
// Date : 12 August 2016
// Version : 1.0
// Author : Vigneshwer

// creating a new socket connection
var socket = new WebSocket("ws://127.0.0.1:8888/ws");

// socket function to interact with the web server
socket.onopen = function() {
	console.log("connected to web socket");
}

socket.onmessage = function(message) {
	console.log("Recieving :-" + message.data);
	var json_data = JSON.parse(message.data);
	// console.log(json_data);
	// var json_data_array = [json_data];
	delete_entries();
	for (var key in json_data) {
		if (json_data.hasOwnProperty(key)) {
    		// console.log(key + " -> " + json_data[key]);
			populate_data(key,json_data[key]);
		}
	}
}

socket.onclose = function() {
	console.log("Disconnected to web socket");
}

//function to delete all the table enteries
var delete_entries = function() {
	tabBody=document.getElementsByTagName("tbody").item(0)
	while(tabBody.rows.length > 0) {
  		tabBody.deleteRow(0);
	}
}

//function to populate the table enteries with the data rxd from the webscoket
var populate_data =function(message_key,message_data) {

	tabBody=document.getElementsByTagName("tbody").item(0);
	row=document.createElement("tr");
	cell1 = document.createElement("td");
	cell2 = document.createElement("td");
	textnode1=document.createTextNode(message_key);
	textnode2=document.createTextNode(message_data);
	cell1.appendChild(textnode1);
	cell2.appendChild(textnode2);
	row.appendChild(cell1);
	row.appendChild(cell2);
	tabBody.appendChild(row);
}

// Sending data from UI to the web server via the socket
var sendMessage = function (message) {
	// console.log("Sending:" +message.data);
	socket.send(message.data);
}

var set_green_color = 0;
// To change the button color and start the cull service with the web socket
function set_cull_button_color(btn) {
	var property = document.getElementById(btn);
	var property_val = document.getElementById(["timer_value"]).value;
	
	try_again: {
		// Set the button color to green
		if (set_green_color == 0) {
			// check if an value is empty or not
			val_status = check_null(property_val)
			if (val_status == true)
			{
				sendMessage({ 'data' : property_val});
				console.log("Cull service Started");
				property.style.backgroundColor = "#4CAF50";
				set_green_color = 1;	
			}
			else{
				alert("Enter a timer value");
				break try_again;
			}
		}
		// Set the button color to red
		else {
			console.log("Cull service stopped");
			property.style.backgroundColor = "#f44336";
			set_green_color = 0;
		}
	}
}

// to check if the entry is null or not
function check_null(property) {
	// console.log("checked if null or not");
	// console.log(property);
	if (property == "" || property == null || property == " ") 
	{
		return false;
	}
	else
	{
		return true;
	}
}